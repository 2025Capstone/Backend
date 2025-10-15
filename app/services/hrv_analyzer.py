import pandas as pd
import neurokit2 as nk
import numpy as np
from scipy.stats import chi2, f
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from firebase_admin import db


# PPG 신호에서 피크를 찾는 헬퍼 함수
def _find_prominent_peaks(sig, threshold=0.1, min_y=0):
    peaks = []
    for i in range(1, len(sig) - 1):
        if sig[i] > sig[i - 1] and sig[i] > sig[i + 1] and sig[i] > min_y:
            L = min(sig[max(0, i - 5):i])
            R = min(sig[i + 1:i + 6])
            if sig[i] - max(L, R) > threshold:
                peaks.append(i)
    return peaks


# 메인 분석 함수 (전체 로직 포함)
def compute_hrv_and_features_from_firebase(session_id: str, alpha=0.05, fs=25):
    """
    Firebase에서 PPG 데이터를 가져와 HRV 특징 계산 및 이상탐지를 수행합니다.
    """
    # 1) Firebase에서 PPG 데이터 불러오기
    ppg_node = db.reference(f"{session_id}/PPG_Data").get() or {}
    timestamps, ppg = [], []
    for k, v in ppg_node.items():
        if not v.get("isError", False):
            timestamps.append(pd.to_datetime(v["timestamp"]))
            ppg.append(v["ppgGreen"])

    if len(ppg) < fs * 2:
        raise ValueError("PPG 데이터가 HRV 분석을 하기에 충분하지 않습니다.")

    # 2) DataFrame 생성 및 정렬
    df = pd.DataFrame({"Timestamp": timestamps, "PPG": ppg}).sort_values("Timestamp")

    # 3) 신호 정제 & 피크 검출
    clean = nk.ppg_clean(df["PPG"], sampling_rate=fs)
    idx = _find_prominent_peaks(clean)
    ts_peaks = df["Timestamp"].iloc[idx].values

    # 4) 2분 세그먼트마다 HRV 지표 계산
    hrv_segments = []
    i = 0
    while i < len(ts_peaks):
        seg_start_ts = ts_peaks[i]
        seg_end_ts = seg_start_ts + pd.Timedelta(minutes=2)

        peak_indices_in_seg = []
        while i < len(ts_peaks) and ts_peaks[i] < seg_end_ts:
            peak_indices_in_seg.append(idx[i])
            i += 1

        if len(peak_indices_in_seg) < 2:
            continue

        # --- [추가된 부분 1] 전체 HRV 지표 생성 ---

        # Time-domain
        rri = np.diff(df["Timestamp"].iloc[peak_indices_in_seg].values).astype('timedelta64[ms]').astype(int)
        hr = 60000 / rri

        hrv_time = nk.hrv_time(peak_indices_in_seg, sampling_rate=fs)
        time_metrics = {
            "mean_nni": hrv_time["HRV_MeanNN"].iloc[0],
            "median_nni": hrv_time["HRV_MedianNN"].iloc[0],
            "range_nni": hrv_time["HRV_MaxNN"].iloc[0] - hrv_time["HRV_MinNN"].iloc[0],
            "sdnn": hrv_time["HRV_SDNN"].iloc[0],
            "sdsd": hrv_time["HRV_SDSD"].iloc[0],
            "rmssd": hrv_time["HRV_RMSSD"].iloc[0],
            "nni_50": int(np.sum(np.abs(np.diff(rri)) > 50)),
            "pnni_50": hrv_time["HRV_pNN50"].iloc[0],
            "nni_20": int(np.sum(np.abs(np.diff(rri)) > 20)),
            "pnni_20": hrv_time["HRV_pNN20"].iloc[0],
            "cvsd": hrv_time["HRV_CVSD"].iloc[0],
            "cvnni": hrv_time["HRV_CVNN"].iloc[0],
            "mean_hr": np.nanmean(hr),
            "min_hr": np.nanmin(hr),
            "max_hr": np.nanmax(hr),
            "std_hr": np.nanstd(hr, ddof=1),
        }

        # Freq-domain
        hrv_freq = nk.hrv_frequency(peak_indices_in_seg, sampling_rate=fs, normalize=False)
        if not hrv_freq.empty:
            freq_metrics = {
                "power_lf": hrv_freq["HRV_LF"].iloc[0],
                "power_hf": hrv_freq["HRV_HF"].iloc[0],
                "total_power": hrv_freq["HRV_TP"].iloc[0],
                "lf_hf_ratio": hrv_freq["HRV_LFHF"].iloc[0]
            }
        else:
            freq_metrics = {k: np.nan for k in ["power_lf", "power_hf", "total_power", "lf_hf_ratio"]}

        # Nonlinear-domain
        hrv_nl = nk.hrv_nonlinear(peak_indices_in_seg, sampling_rate=fs)
        if not hrv_nl.empty:
            nonlinear_metrics = {
                "csi": float(hrv_nl["HRV_CSI"].iloc[0]),
                "cvi": float(hrv_nl["HRV_CVI"].iloc[0]),
                "modified_csi": float(hrv_nl["HRV_CSI_Modified"].iloc[0]),
                "sampen": float(hrv_nl["HRV_SampEn"].iloc[0])
            }
        else:
            nonlinear_metrics = {k: np.nan for k in ["csi", "cvi", "modified_csi", "sampen"]}

        hrv_segments.append({
            "segment_start_ts": seg_start_ts,
            "time": time_metrics, "freq": freq_metrics, "nonlinear": nonlinear_metrics
        })

    # 결과 리스트를 DataFrame으로 변환
    results_list = []
    if not hrv_segments:
        raise ValueError("HRV 세그먼트를 생성할 수 없습니다.")

    t0 = hrv_segments[0]["segment_start_ts"]
    for res in hrv_segments:
        row = {"timestamp": (res["segment_start_ts"] - t0).total_seconds()}
        for domain, metrics in res.items():
            if isinstance(metrics, dict):
                for key, val in metrics.items():
                    row[f"{domain}_{key}"] = val
        results_list.append(row)

    df_wearable_features = pd.DataFrame(results_list)

    # 5) MSPC-PCA 이상탐지
    N = len(df_wearable_features)
    if N <= 1:  # 데이터가 1개 이하일 경우 PCA/통계 분석이 불가
        return df_wearable_features

    # --- [추가된 부분 2] MSPC-PCA 이상탐지 로직 ---
    domains = {
        "Time": df_wearable_features.filter(regex="^time_").columns,
        "Freq": df_wearable_features.filter(regex="^freq_").columns,
        "Nonlinear": df_wearable_features.filter(regex="^nonlinear_").columns
    }

    for domain, cols in domains.items():
        if cols.empty:
            continue
        # 1) 데이터 준비 및 표준화
        X = df_wearable_features[cols].fillna(0).values.astype(float)
        X_scaled = StandardScaler().fit_transform(X)

        # 2) PCA (단일 주성분)
        pca = PCA(n_components=1).fit(X_scaled)
        scores = pca.transform(X_scaled).flatten()
        var1 = pca.explained_variance_[0]

        # 3) Hotelling’s T² 계산
        T2 = (scores ** 2) / var1
        ulc_t2 = ((N + 1) * (N - 1) / (N * (N - 1))) * f.ppf(1 - alpha, 1, N - 1)

        # 4) SPE 계산
        X_hat = pca.inverse_transform(scores.reshape(-1, 1))
        SPE = ((X_scaled - X_hat) ** 2).sum(axis=1)
        b, v = SPE.mean(), SPE.var()
        if b == 0 or v == 0:  # 분모가 0이 되는 경우 방지
            ulc_spe = np.inf
        else:
            df_chi = (2 * b * b) / v
            ulc_spe = (v / (2 * b)) * chi2.ppf(1 - alpha, df_chi)

        T2_Anomaly_Score = T2 / ulc_t2 if ulc_t2 > 0 else np.inf
        SPE_Anomaly_Score = SPE / ulc_spe if ulc_spe > 0 else np.inf
        anomaly_flag = ((T2 >= ulc_t2) | (SPE >= ulc_spe)).astype(int)

        # 5) DataFrame에 컬럼 추가
        df_wearable_features[f"{domain}_T2_Score"] = T2_Anomaly_Score
        df_wearable_features[f"{domain}_SPE_Score"] = SPE_Anomaly_Score
        df_wearable_features[f"{domain}_Anomaly"] = anomaly_flag

    return df_wearable_features