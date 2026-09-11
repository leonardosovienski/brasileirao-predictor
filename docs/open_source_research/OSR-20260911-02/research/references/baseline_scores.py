import numpy as np

def log_loss_matrix(P: np.ndarray, Y: np.ndarray, eps: float = 1e-12) -> float:
    """Log-Loss (Cross-Entropy) vetorizado para matrizes de placar (N, G, G).
    P: probabilidades previstas; Y: one-hot. Sem loops Python nativos."""
    return float(-np.sum(Y * np.log(np.clip(P, eps, 1.0))) / P.shape[0])


def brier_score_multiclass(P: np.ndarray, Y: np.ndarray) -> float:
    """Brier Score Multi-Class vetorizado. BS = mean_n Σ_{i,j} (P_{n,i,j} - Y_{n,i,j})².
    P, Y: (N, G, G). Varia em [0, 2] para k classes (aqui k=G²)."""
    return float(np.mean(np.sum((P - Y) ** 2, axis=(1, 2))))
