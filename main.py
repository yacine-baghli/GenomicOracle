from flask import Flask, render_template, request, make_response, session, redirect, url_for, jsonify
import os
import secrets
from io import BytesIO
import vcfpy
from xhtml2pdf import pisa
from qml_module import run_qml_simulation
from llm_module import generate_treatment_recommendations
from vqs_client import vqs
from ai_engine import score_case, rank_cases, generate_case_summary_llm

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = secrets.token_hex(16)

# Helper function to render HTML to PDF using xhtml2pdf
def render_pdf(html):
    """Renders HTML to a PDF in memory."""
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None

def get_clinvar_annotation(hgvs_notation):
    # Placeholder for ClinVar API call
    hgvs_upper = hgvs_notation.upper()
    pathogenic_variants = [
        "L858R", "R273H", "G12C", "T790M", "G12V", "E545K", "R876*", 
        "V600E", "R130G", "R58*", "H1047R", "D538G", "S1982FS", 
        "AMPLIFICATION", "F1174L", "FUSION"
    ]
    
    for variant in pathogenic_variants:
        if variant in hgvs_upper:
            return {"clinical_significance": "Pathogenic", "review_status": "reviewed by expert panel"}
            
    return {"clinical_significance": "Uncertain significance", "review_status": "no assertion provided"}

@app.route('/')
def index():
    llm_provider = session.get('llm_provider', 'gemini')
    api_key_set = bool(session.get('api_key'))
    return render_template('index.html', llm_provider=llm_provider, api_key_set=api_key_set)

@app.route('/settings', methods=['POST'])
def save_settings():
    session['llm_provider'] = request.form.get('llm_provider')
    session['api_key'] = request.form.get('api_key')
    return redirect(url_for('index'))

@app.route('/analysis', methods=['GET', 'POST'])
def analysis():
    if request.method == 'POST':
        patient_info = {
            'name': request.form['name'],
            'age': request.form['age'],
            'gender': request.form['gender'],
            'condition': request.form['condition']
        }
        
        variants = []
        
        if 'vcf_file' in request.files and request.files['vcf_file'].filename != '':
            vcf_file = request.files['vcf_file']
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], vcf_file.filename)
            vcf_file.save(filepath)
            
            reader = vcfpy.Reader.from_path(filepath)
            for record in reader:
                gene_name_list = record.INFO.get('GENE', [])
                gene_name = gene_name_list[0] if gene_name_list else 'N/A'
                hgvs = f"{record.CHROM}:{record.POS} {record.REF}>{record.ALT[0].value}"
                call = record.calls[0]
                zygosity = 'heterozygous' if call.is_het else 'homozygous' if call.is_hom_alt else 'reference'

                variant_info = {'gene': gene_name, 'hgvs': hgvs, 'zygosity': zygosity}
                variant_info.update(get_clinvar_annotation(hgvs))
                variant_info['qml_score'] = run_qml_simulation(variant_info)
                variants.append(variant_info)
        else:
            genes = request.form.getlist('gene[]')
            hgvss = request.form.getlist('hgvs[]')
            zygosities = request.form.getlist('zygosity[]')

            qml_trained = session.get('qml_trained_weights', False)

            for i in range(len(genes)):
                if genes[i]:
                    variant_info = {'gene': genes[i], 'hgvs': hgvss[i], 'zygosity': zygosities[i]}
                    variant_info.update(get_clinvar_annotation(hgvss[i]))
                    variant_info['qml_score'] = run_qml_simulation(variant_info, trained=qml_trained)
                    
                    if qml_trained:
                        from qml_module import extract_vqc_feature
                        variant_info['vqc_feature'] = extract_vqc_feature(variant_info)
                        
                    variants.append(variant_info)

            from qml_module import simulate_quantum_combinatorial_search
            session['quantum_results'] = simulate_quantum_combinatorial_search(variants)

        session['patient_info'] = patient_info
        session['variants'] = variants

        return render_template('analysis.html', patient_info=patient_info, variants=variants)
    
    return render_template('analysis.html')

@app.route('/results')
def results():
    patient_info = session.get('patient_info', {'name': 'John Doe (Mock Data)', 'age': 55, 'gender': 'male', 'condition': 'Lung Adenocarcinoma'})
    variants = session.get('variants', [
        {'gene': 'EGFR', 'hgvs': 'p.L858R', 'zygosity': 'heterozygous', 'clinical_significance': 'Pathogenic', 'review_status': 'reviewed by expert panel', 'qml_score': 0.85},
        {'gene': 'TP53', 'hgvs': 'p.R273H', 'zygosity': 'heterozygous', 'clinical_significance': 'Pathogenic', 'review_status': 'reviewed by expert panel', 'qml_score': 0.72},
        {'gene': 'KRAS', 'hgvs': 'p.G12C', 'zygosity': 'heterozygous', 'clinical_significance': 'Likely Pathogenic', 'review_status': 'criteria provided, multiple submitters', 'qml_score': 0.61}
    ])
    
    try:
        llm_provider = session.get('llm_provider')
        api_key = session.get('api_key')
        treatment_html = generate_treatment_recommendations(patient_info, variants, llm_provider, api_key)
        # Clean markdown backticks if LLM mistakenly returns them
        if treatment_html.strip().startswith('```html'):
            treatment_html = treatment_html.strip()[7:]
        if treatment_html.strip().endswith('```'):
            treatment_html = treatment_html.strip()[:-3]
    except Exception as e:
        treatment_html = f"<p style='color: var(--danger);'>Error generating recommendations: {e}</p>"

    quantum_results = session.get('quantum_results', {})
    return render_template('results.html', patient_info=patient_info, variants=variants, treatment_html=treatment_html, quantum_results=quantum_results)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json()
    message = data.get('message', '')
    history = data.get('history', []) 
    
    patient_info = session.get('patient_info', {})
    variants = session.get('variants', [])
    llm_provider = session.get('llm_provider')
    api_key = session.get('api_key')
    
    conversation_history = history + [{"role": "user", "content": message}]
    
    from llm_module import chat_with_llm
    response_text = chat_with_llm(patient_info, variants, conversation_history, llm_provider, api_key)
    
    return jsonify({"response": response_text})

@app.route('/training')
def training():
    return render_template('training.html')

@app.route('/api/train_model', methods=['POST'])
def api_train_model():
    session['qml_trained_weights'] = True
    return jsonify({"status": "success"})

@app.route('/download_pdf')
def download_pdf():
    patient_info = {'name': 'John Doe', 'age': 55, 'gender': 'male', 'condition': 'Lung Adenocarcinoma'}
    variants = [
        {'gene': 'EGFR', 'hgvs': 'p.L858R', 'zygosity': 'heterozygous', 'clinical_significance': 'Pathogenic', 'review_status': 'reviewed by expert panel', 'qml_score': 0.85},
        {'gene': 'TP53', 'hgvs': 'p.R273H', 'zygosity': 'heterozygous', 'clinical_significance': 'Pathogenic', 'review_status': 'reviewed by expert panel', 'qml_score': 0.72},
        {'gene': 'KRAS', 'hgvs': 'p.G12C', 'zygosity': 'heterozygous', 'clinical_significance': 'Likely Pathogenic', 'review_status': 'criteria provided, multiple submitters', 'qml_score': 0.61}
    ]
    
    # Render the template with data
    rendered_html = render_template('results_pdf.html', patient_info=patient_info, variants=variants)
    
    # Generate the PDF
    pdf_data = render_pdf(rendered_html)
    
    if pdf_data:
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f"attachment; filename=Genomic_Report_{patient_info['name']}.pdf"
        return response
    
    return "Error generating PDF", 500

# ─── Co-Pilot Dashboard ────────────────────────────────────────────────────

@app.route('/copilot')
def copilot():
    return render_template('copilot.html')

@app.route('/api/copilot/analyze', methods=['POST'])
def copilot_analyze():
    """Connect to VQS, fetch variants for each dataset key, score and rank."""
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    dataset_keys = data.get('dataset_keys', [])
    llm_provider = data.get('llm_provider', 'none')

    auth_result = vqs.authenticate(username, password)
    if not auth_result.get('success'):
        return jsonify({"success": False, "error": f"Auth failed: {auth_result.get('error', 'Unknown')}"})

    cases = {}
    for i, key in enumerate(dataset_keys):
        key = key.strip()
        if not key:
            continue
        case_id = f"Sample {chr(65+i)} — Dataset {i+1}"
        result = vqs.query_variants(
            dataset_key=key, columns=["*"],
            pagination={"offset": 0, "limit": 500},
        )
        if result.get("success") and result.get("data"):
            cases[case_id] = result["data"]
        else:
            cases[case_id] = []

    if not cases:
        return jsonify({"success": False, "error": "No data returned from VQS for any key."})

    ranked = rank_cases(cases)
    api_key = session.get('api_key', '')
    for case in ranked:
        if llm_provider != 'none':
            case['summary'] = generate_case_summary_llm(case, llm_provider, api_key)
        else:
            from ai_engine import _generate_fallback_summary
            case['summary'] = _generate_fallback_summary(case)

    return jsonify({"success": True, "ranked_cases": ranked})

@app.route('/api/copilot/csv', methods=['POST'])
def copilot_csv():
    """Upload a CSV file, parse it, score and rank cases."""
    from ai_engine import parse_csv_to_cases
    llm_provider = request.form.get('llm_provider', 'none')

    if 'csv_file' not in request.files:
        return jsonify({"success": False, "error": "No CSV file uploaded."})

    csv_file = request.files['csv_file']
    if csv_file.filename == '':
        return jsonify({"success": False, "error": "Empty filename."})

    try:
        csv_text = csv_file.read().decode('utf-8')
    except UnicodeDecodeError:
        csv_text = csv_file.read().decode('latin-1')

    cases = parse_csv_to_cases(csv_text)
    if not cases:
        return jsonify({"success": False, "error": "No data found in CSV."})

    ranked = rank_cases(cases)
    api_key = session.get('api_key', '')
    for case in ranked:
        if llm_provider != 'none':
            case['summary'] = generate_case_summary_llm(case, llm_provider, api_key)
        else:
            from ai_engine import _generate_fallback_summary
            case['summary'] = _generate_fallback_summary(case)

    return jsonify({"success": True, "ranked_cases": ranked})

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
