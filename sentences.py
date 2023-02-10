# Copied from https://huggingface.co/1-800-BAD-CODE/sentence_boundary_detection_multilang

from sentencepiece import SentencePieceProcessor
import onnxruntime as ort
import numpy as np
from huggingface_hub import hf_hub_download
from typing import List

spe_path = hf_hub_download(
    repo_id="1-800-BAD-CODE/sentence_boundary_detection_multilang", filename="spe_mixed_case_64k_49lang.model"
)
onnx_path = hf_hub_download(
    repo_id="1-800-BAD-CODE/sentence_boundary_detection_multilang", filename="sbd_49lang_bert_small.onnx"
)

tokenizer: SentencePieceProcessor = SentencePieceProcessor(spe_path)
ort_session: ort.InferenceSession = ort.InferenceSession(onnx_path)

def run_infer(text: str, threshold: float = 0.5):
    # Encode as IDs for the model input; add BOS/EOS tags.
    ids = tokenizer.EncodeAsIds(text)
    input_ids = np.array([[tokenizer.bos_id()] + ids + [tokenizer.eos_id()]])
    # Run inference; get probablity of each token being a sentence boundary
    outputs = ort_session.run(None, {"input_ids": input_ids})
    # Shape [B, T]
    probs = outputs[0]
    # Single input is batched; keep only first element
    probs = probs[0]
    # Trim BOS/EOS
    probs = probs[1:-1]
    # Find all positions that exceed the threshold as a sentence boundary
    break_points: List[int] = np.squeeze(np.argwhere(probs > threshold), axis=1).tolist()  # noqa
    # Add the final token to the break points, to not have leftover tokens after the loop
    if (not break_points) or (break_points[-1] != len(ids) - 1):
        break_points.append(len(ids) - 1)
    # Break tokens at boundaries, convert back to text
    for i, break_point in enumerate(break_points):
        start = 0 if i == 0 else (break_points[i - 1] + 1)
        sub_ids = ids[start : break_point + 1]
        sub_text = tokenizer.DecodeIds(sub_ids)
        yield sub_text