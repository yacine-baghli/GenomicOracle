import os
import json

def get_system_prompt():
    return """You are an expert Clinical Genomic Oncologist. 
You are given a patient profile and a list of identified genomic variants (with their ClinVar significance and Pathogenicity score).
Your task is to provide strict, evidence-based treatment recommendations based on standardized oncological guidelines (e.g., NCCN, ESMO).
Format the output as clean, beautiful HTML using semantic tags (<h3>, <ul>, <li>, <strong>) without any Markdown backticks (```html).
Do not include <html> or <body> tags, just the inner HTML elements to be injected into a panel.
Focus on identifying first-line therapies (like Osimertinib for EGFR L858R) and potential clinical trials. Ensure the tone is highly professional and clinical.
"""

def generate_treatment_recommendations(patient_info, variants, llm_provider=None, api_key=None):
    prompt = f"Patient Info: {json.dumps(patient_info)}\nVariants: {json.dumps(variants)}"
    
    # Use explicitly passed key or fallback to env
    openai_key = api_key if llm_provider == 'openai' else os.environ.get("OPENAI_API_KEY")
    anthropic_key = api_key if llm_provider == 'anthropic' else os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = api_key if llm_provider == 'gemini' else os.environ.get("GEMINI_API_KEY")

    # Check OpenAI
    if openai_key and (not llm_provider or llm_provider == 'openai'):
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI error: {e}")
            
    # Check Anthropic
    if anthropic_key and (not llm_provider or llm_provider == 'anthropic'):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1500,
                system=get_system_prompt(),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            print(f"Anthropic error: {e}")

    # Check Gemini
    if gemini_key and (not llm_provider or llm_provider == 'gemini'):
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=get_system_prompt(),
                ),
            )
            return response.text
        except Exception as e:
            print(f"Gemini error: {e}")

    # Fallback Expert System if no API keys map to the correct treatments for common variants
    return _generate_fallback_html(patient_info, variants)

def _generate_fallback_html(patient_info, variants):
    variant_details = [(str(v.get('gene', '')).upper(), str(v.get('hgvs', '')).upper()) for v in variants]
    genes = [v[0] for v in variant_details]
    
    html = f"<h3 style='color: var(--primary); border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; margin-bottom: 1.5rem;'>Clinical Oncology Report: {patient_info.get('condition', 'Condition')}</h3>"
    html += "<div style='background: rgba(245, 158, 11, 0.1); border-left: 4px solid var(--warning); padding: 10px; border-radius: 4px; margin-bottom: 1.5rem;'>"
    html += "<p style='color: #fcd34d; margin: 0; font-size: 0.9rem;'><strong>System Notice:</strong> Operating in Offline Deterministic Mode (No LLM API Key detected). Expert rule-base engaged.</p>"
    html += "</div>"
    
    html += "<h4 style='color: var(--text-main); margin-bottom: 1rem;'>1. Primary Targeted Therapies</h4>"
    html += "<ul style='padding-left: 1.5rem; margin-bottom: 2rem; color: var(--text-muted);'>"
    
    matched = False
    for gene, hgvs in variant_details:
        if gene == 'EGFR':
            if 'T790M' in hgvs:
                html += "<li style='margin-bottom: 0.75rem;'><strong style='color: var(--success);'>Osimertinib (Tagrisso)</strong>: Indicated as patients with EGFR T790M acquired resistance mutations respond favorably to 3rd-generation TKIs. First and second-generation TKIs (Erlotinib, Gefitinib, Afatinib) are contraindicated due to resistance.</li>"
                matched = True
            elif 'L858R' in hgvs or '19' in hgvs:
                html += "<li style='margin-bottom: 0.75rem;'><strong style='color: var(--success);'>Osimertinib (Tagrisso)</strong>: Preferred first-line therapy for sensitizing EGFR mutations (L858R or Exon 19 deletions). Improves overall survival and CNS penetration compared to earlier generation TKIs.</li>"
                matched = True
        elif gene == 'KRAS':
            if 'G12C' in hgvs:
                html += "<li style='margin-bottom: 0.75rem;'><strong style='color: var(--success);'>Sotorasib (Lumakras) / Adagrasib</strong>: Indicated specifically for the KRAS G12C mutation. Offers targeted inhibition binding to the GDP-bound state of KRAS.</li>"
                matched = True
            else:
                html += "<li style='margin-bottom: 0.75rem;'><strong>Chemotherapy + Immunotherapy</strong>: Standard of care for non-G12C KRAS mutations. No direct specific inhibitors are currently FDA-approved for your specific KRAS variant.</li>"
                matched = True
        elif gene == 'BRAF' and 'V600E' in hgvs:
            html += "<li style='margin-bottom: 0.75rem;'><strong style='color: var(--success);'>Dabrafenib + Trametinib</strong>: BRAF/MEK inhibitor combination therapy is the standard of care for BRAF V600E mutated cases, preventing paradoxical MAP kinase pathway activation.</li>"
            matched = True
        elif gene == 'PIK3CA':
            html += "<li style='margin-bottom: 0.75rem;'><strong style='color: var(--success);'>Alpelisib (Piqray) + Fulvestrant</strong>: Approved for HR-positive, HER2-negative advanced breast cancer with a PIK3CA mutation.</li>"
            matched = True
        elif gene == 'ALK':
            html += "<li style='margin-bottom: 0.75rem;'><strong style='color: var(--success);'>Alectinib / Lorlatinib</strong>: Highly active next-generation ALK inhibitors with excellent CNS penetration, preferred in the frontline setting over Crizotinib.</li>"
            matched = True
        elif gene == 'ESR1':
            html += "<li style='margin-bottom: 0.75rem;'><strong style='color: var(--success);'>Elacestrant (Orserdu)</strong>: An oral SERD indicated for ER+, HER2- advanced breast cancer with an ESR1 mutation, which typically confers resistance to aromatase inhibitors.</li>"
            matched = True
        elif gene == 'MYCN':
             html += "<li style='margin-bottom: 0.75rem;'><strong style='color: var(--danger);'>Intensive Multi-modal Therapy</strong>: MYCN amplification signifies high-risk neuroblastoma. Standard protocol involves induction chemotherapy (e.g., COJEC), surgical resection, myeloablative chemotherapy with stem cell rescue, radiotherapy, and Dinutuximab.</li>"
             matched = True

    if not matched:
         html += "<li style='margin-bottom: 0.75rem;'><strong>Standard Cytotoxic Chemotherapy</strong>: Follow NCCN guidelines for the primary tumor site. No clear actionability for targeted inhibition pathways identified.</li>"

    html += "</ul>"

    html += "<h4 style='color: var(--text-main); margin-bottom: 1rem;'>2. Prognosis & Co-occurring Mutations</h4>"
    html += "<ul style='padding-left: 1.5rem; margin-bottom: 2rem; color: var(--text-muted);'>"
    prognosis_rendered = False
    for gene, hgvs in variant_details:
        if gene == 'TP53':
             html += "<li style='margin-bottom: 0.75rem;'><strong>TP53 Mutation</strong>: Indicates potential genomic instability and poorer outcomes. Resistance to primary targeted therapy may emerge more rapidly. Re-biopsy at progression (liquid or tissue) is highly recommended to monitor clonal evolution.</li>"
             prognosis_rendered = True
        elif gene == 'PTEN':
             html += "<li style='margin-bottom: 0.75rem;'><strong>PTEN Loss/Mutation</strong>: Co-occurrence suggests PI3K/AKT/mTOR pathway activation. May reduce the efficacy of primary MAP-kinase targeted agents (e.g. BRAF inhibitors in melanoma).</li>"
             prognosis_rendered = True
        elif gene == 'APC':
             html += "<li style='margin-bottom: 0.75rem;'><strong>APC Mutation</strong>: Canonical driver event, predominantly seen in colorectal pathways (Wnt signaling). Prognostically neutral but diagnostically reinforcing.</li>"
             prognosis_rendered = True

    if not prognosis_rendered:
         html += "<li style='margin-bottom: 0.75rem;'>No major secondary resistance markers or negative prognostic co-mutations detected in the current panel. Follow standard monitoring.</li>"
    html += "</ul>"

    html += "<h4 style='color: var(--text-main); margin-bottom: 1rem;'>3. Clinical Trial Opportunities</h4>"
    html += "<p style='color: var(--text-muted); line-height: 1.6; margin-bottom: 0;'>"
    if 'KRAS' in genes:
         html += "We recommend screening for PAN-KRAS inhibitor trials (e.g., currently recruiting Revolution Medicines RMC-6236 Phase II trials) as well as combinations of immune checkpoint inhibitors + targeted agents."
    elif 'EGFR' in genes and 'T790M' in str(variant_details):
         html += "Consider 4th generation EGFR inhibitor trials (e.g., BLU-945, JNJ-61186372) aimed at overcoming complex C797S acquired resistance if progression on Osimertinib occurs."
    else:
         html += "Discuss potential enrollment in national molecular profiling umbrellas like the NCI-MATCH or targeted basket trials if progression on standard therapy occurs. Molecular tumor board review is advised."
    html += "</p>"

    return html

def chat_with_llm(patient_info, variants, conversation_history, llm_provider=None, api_key=None):
    context_prompt = f"Patient Info: {json.dumps(patient_info)}\nVariants: {json.dumps(variants)}\nYou are GenomicOracle, an expert Clinical Genomic Oncologist AI. Answer questions regarding this patient's genomic profile and treatment recommendations with absolute highest clinical accuracy. Keep responses extremely concise but medical."
    
    # Default to anthropic if None, based on user preference
    if not llm_provider:
        llm_provider = 'anthropic'

    openai_key = api_key if llm_provider == 'openai' else os.environ.get("OPENAI_API_KEY")
    anthropic_key = api_key if llm_provider == 'anthropic' else os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = api_key if llm_provider == 'gemini' else os.environ.get("GEMINI_API_KEY")
    
    auth_warning = "Please click the '⚙ LLM Settings' gear icon on the main page to input an active API key."

    if llm_provider == 'openai' and openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            messages = [{"role": "system", "content": context_prompt}] + conversation_history
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            return response.choices[0].message.content
        except ImportError:
            return f"OpenAI module is not installed. {auth_warning}"
        except Exception as e:
            return f"API Error: {e}. {auth_warning}"
            
    elif llm_provider == 'anthropic' and anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=600,
                system=context_prompt,
                messages=conversation_history
            )
            return response.content[0].text
        except ImportError:
            return f"Claude (Anthropic) module is not installed. {auth_warning}"
        except Exception as e:
            return f"API Error: {e}. {auth_warning}"

    elif llm_provider == 'gemini' and gemini_key:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_key)
            
            gemini_history = []
            for msg in conversation_history:
                role = "user" if msg['role'] == "user" else "model"
                gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg['content'])]))
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=gemini_history,
                config=types.GenerateContentConfig(
                    system_instruction=context_prompt,
                ),
            )
            return response.text
        except ImportError:
            return f"Google GenAI module is not installed. {auth_warning}"
        except Exception as e:
            return f"API Error: {e}. {auth_warning}"
            
    return auth_warning
