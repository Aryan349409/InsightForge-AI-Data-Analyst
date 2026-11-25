"""Predictive analytics: auto-ML (classification/regression), forecasting, clustering."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (GradientBoostingClassifier, GradientBoostingRegressor,
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, f1_score, mean_absolute_error,
                             r2_score, silhouette_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from modules.profiling import semantic_type


def detect_task(y: pd.Series) -> str:
    if not pd.api.types.is_numeric_dtype(y) or pd.api.types.is_bool_dtype(y):
        return "classification"      # strings, categories, booleans
    if pd.api.types.is_numeric_dtype(y) and y.nunique() <= 10 and y.nunique() / max(len(y), 1) < 0.05:
        return "classification"
    return "regression"


def _prepare_features(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    for c in list(X.columns):
        if pd.api.types.is_datetime64_any_dtype(X[c]):
            X[f"{c}_year"], X[f"{c}_month"], X[f"{c}_dow"] = X[c].dt.year, X[c].dt.month, X[c].dt.dayofweek
            X = X.drop(columns=c)
        elif semantic_type(X[c]) in ("text/id", "identifier") or X[c].nunique() <= 1:
            X = X.drop(columns=c)           # identifiers carry no generalisable signal
        elif not pd.api.types.is_numeric_dtype(X[c]) and X[c].nunique() > 50:
            X = X.drop(columns=c)
    return X


def _pipeline(X: pd.DataFrame, model) -> Pipeline:
    num = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
    cat = [c for c in X.columns if c not in num]
    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat),
    ])
    return Pipeline([("pre", pre), ("model", model)])


def train(df: pd.DataFrame, target: str, test_size: float = 0.2, seed: int = 42) -> dict:
    data = df.dropna(subset=[target]).copy()
    if len(data) < 30:
        raise ValueError("Need at least 30 rows with a non-missing target to train a model.")
    y = data[target]
    X = _prepare_features(data.drop(columns=[target]))
    if X.shape[1] == 0:
        raise ValueError("No usable feature columns after removing IDs/constants.")
    task = detect_task(y)
    if task == "classification":
        y = y.astype(str)
        models = {"Logistic Regression": LogisticRegression(max_iter=1000),
                  "Random Forest": RandomForestClassifier(n_estimators=200, random_state=seed),
                  "Gradient Boosting": GradientBoostingClassifier(random_state=seed)}
    else:
        models = {"Ridge Regression": Ridge(),
                  "Random Forest": RandomForestRegressor(n_estimators=200, random_state=seed),
                  "Gradient Boosting": GradientBoostingRegressor(random_state=seed)}
    stratify = y if task == "classification" and y.value_counts().min() >= 2 else None
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=test_size, random_state=seed, stratify=stratify)

    rows, fitted = [], {}
    for name, m in models.items():
        pipe = _pipeline(Xtr, m)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pipe.fit(Xtr, ytr)
        pred = pipe.predict(Xte)
        if task == "classification":
            rows.append({"model": name, "accuracy": accuracy_score(yte, pred),
                         "f1_weighted": f1_score(yte, pred, average="weighted")})
        else:
            rows.append({"model": name, "r2": r2_score(yte, pred), "mae": mean_absolute_error(yte, pred)})
        fitted[name] = pipe
    comp = pd.DataFrame(rows).round(4)
    key = "f1_weighted" if task == "classification" else "r2"
    best = comp.sort_values(key, ascending=False).iloc[0]["model"]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pi = permutation_importance(fitted[best], Xte, yte, n_repeats=5, random_state=seed, n_jobs=1)
    imp = (pd.DataFrame({"feature": Xte.columns, "importance": pi.importances_mean})
           .sort_values("importance", ascending=False).reset_index(drop=True))

    baseline = (float(yte.value_counts(normalize=True).max()) if task == "classification"
                else float(r2_score(yte, np.full(len(yte), ytr.mean()))))
    return {"task": task, "target": target, "best_model": best, "comparison": comp,
            "importance": imp, "baseline": baseline, "n_train": len(Xtr), "n_test": len(Xte),
            "pipeline": fitted[best], "features": list(X.columns)}


def forecast(df: pd.DataFrame, date_col: str, value_col: str, periods: int = 6,
             freq: str = "MS") -> dict:
    """Aggregate to `freq`, fit Holt-Winters (falls back to linear trend), forecast ahead."""
    s = df.set_index(date_col)[value_col].resample(freq).sum().astype(float)
    if len(s) < 8:
        raise ValueError("Need at least 8 time periods to forecast.")
    holdout = max(2, min(6, len(s) // 4))
    train_s, test_s = s.iloc[:-holdout], s.iloc[-holdout:]

    def fit_predict(series, steps):
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            seasonal = "add" if len(series) >= 24 and freq.startswith("M") else None
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = ExponentialSmoothing(series, trend="add", seasonal=seasonal,
                                         seasonal_periods=12 if seasonal else None).fit()
            return np.asarray(m.forecast(steps)), "Holt-Winters"
        except Exception:
            x = np.arange(len(series))
            slope, icpt = np.polyfit(x, series.values, 1)
            return icpt + slope * np.arange(len(series), len(series) + steps), "Linear trend"

    back, method = fit_predict(train_s, holdout)
    mae = float(mean_absolute_error(test_s, back))
    mape = float(np.mean(np.abs((test_s.values - back) / np.where(test_s.values == 0, np.nan, test_s.values))) * 100)
    fut, _ = fit_predict(s, periods)
    idx = pd.date_range(s.index[-1], periods=periods + 1, freq=freq)[1:]
    return {"history": s, "forecast": pd.Series(fut, index=idx), "method": method,
            "mae": mae, "mape": None if np.isnan(mape) else mape, "holdout": holdout}


def cluster(df: pd.DataFrame, k_max: int = 6, seed: int = 42) -> dict:
    X = df.select_dtypes(include="number").dropna(axis=1, how="all")
    X = X[[c for c in X.columns if semantic_type(X[c]) != "identifier"]]
    X = X.loc[:, X.nunique() > 1]
    if X.shape[1] < 2 or len(X) < 20:
        raise ValueError("Need at least 2 numeric columns and 20 rows for clustering.")
    Xs = StandardScaler().fit_transform(SimpleImputer(strategy="median").fit_transform(X))
    best_k, best_score, scores = 2, -1, {}
    sample = Xs if len(Xs) <= 3000 else Xs[np.random.RandomState(seed).choice(len(Xs), 3000, replace=False)]
    for k in range(2, min(k_max, len(Xs) - 1) + 1):
        labels = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(sample)
        scores[k] = silhouette_score(sample, labels)
        if scores[k] > best_score:
            best_k, best_score = k, scores[k]
    labels = KMeans(n_clusters=best_k, n_init=10, random_state=seed).fit_predict(Xs)
    out = X.copy()
    out["cluster"] = labels
    return {"k": best_k, "silhouette": best_score, "scores": scores,
            "profile": out.groupby("cluster").mean().round(2), "sizes": out["cluster"].value_counts().sort_index(),
            "labelled": out}
