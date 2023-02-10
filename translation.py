from transformers import pipeline

import sentences

translator = pipeline("translation_fi_to_en", model="Helsinki-NLP/opus-mt-fi-en")

def translate(text: str):
    ans = []
    for sentence in sentences.run_infer(text):
        ans.append(translator(sentence)[0]["translation_text"])
    
    return " ".join(ans)