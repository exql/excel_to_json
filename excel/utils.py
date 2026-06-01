
import numpy as np

def convertir_tipo(obj):
    if isinstance(obj, (np.generic, np.int64, np.float64)):
        return obj.item()
    return obj
