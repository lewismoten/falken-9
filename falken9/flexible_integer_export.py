"""Four-expert effective F9F1 to existing F9J2; no new arithmetic contract."""
from falken9.canonical_integer_export import convert as _convert, save, load
from falken9.integer_export import MATRICES


def convert(model, frac=11, matrix_bits=16, activation_bits=32,
            attention_mode='early', interpolate=True, component_int8=()):
    # Flexible K=1 uses a full-E gate, unlike the F9J2 selected-score gate.
    if model.config.active != 2:
        raise ValueError('only top-2 selected-softmax conversion is supported')
    if any(name not in MATRICES for name in component_int8):
        raise ValueError('component reduction requires a matrix name')
    candidate = _convert(model, frac, matrix_bits, activation_bits, attention_mode, interpolate)
    if component_int8:
        # Quantize effective F9F1 weights directly, never re-round W16 codes.
        low = _convert(model, frac, 8, activation_bits, attention_mode, interpolate)
        for name in component_int8:
            candidate['tensors'][name] = low['tensors'][name]
    return candidate
