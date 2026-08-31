from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

TRAINING_DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_training_dataset"
    / "fii_training_dataset.parquet"
)

PRICE_QUALITY_PATH = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "quality"
    / "fii_price_quality"
    / "fii_price_quality.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "gold"
    / "ml"
    / "fii_ml_eligibility"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "fii_ml_eligibility.parquet"
)


ML_ELIGIBILITY_VERSION = "v1"

FEATURE_WINDOW_OBSERVATIONS = 20

EXPECTED_TARGET_HORIZON = 5
EXPECTED_TARGET_HORIZON_SEMANTICS = (
    "GLOBAL_B3_TRADING_DAYS"
)


def load_training_dataset() -> pd.DataFrame:
    if not TRAINING_DATASET_PATH.exists():
        raise FileNotFoundError(
            "Training Dataset não encontrado: "
            f"{TRAINING_DATASET_PATH}"
        )

    print(
        "Carregando FII Training Dataset..."
    )

    return pd.read_parquet(
        TRAINING_DATASET_PATH
    )


def normalize_training_schema(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    required_source_columns = [
        "feature_date",
        "ticker",
        "target_date_next_5d",
        "target_horizon",
        "target_horizon_semantics",
        "target_return_next_5d",
    ]

    missing_columns = [
        column
        for column in required_source_columns
        if column not in result.columns
    ]

    if missing_columns:
        raise ValueError(
            "Training Dataset v2 não possui "
            "as colunas esperadas: "
            f"{missing_columns}"
        )

    #
    # Internamente padronizamos o nome
    # target_date para simplificar a camada
    # de elegibilidade.
    #
    result = result.rename(
        columns={
            "target_date_next_5d": (
                "target_date"
            )
        }
    )

    result[
        "feature_date"
    ] = pd.to_datetime(
        result[
            "feature_date"
        ]
    )

    result[
        "target_date"
    ] = pd.to_datetime(
        result[
            "target_date"
        ]
    )

    result[
        "ticker"
    ] = (
        result[
            "ticker"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return result


def load_price_quality() -> pd.DataFrame:
    if not PRICE_QUALITY_PATH.exists():
        raise FileNotFoundError(
            "FII Price Quality não encontrado: "
            f"{PRICE_QUALITY_PATH}"
        )

    print(
        "Carregando FII Price Quality..."
    )

    dataframe = pd.read_parquet(
        PRICE_QUALITY_PATH
    )

    dataframe[
        "trade_date"
    ] = pd.to_datetime(
        dataframe[
            "trade_date"
        ]
    )

    dataframe[
        "ticker"
    ] = (
        dataframe[
            "ticker"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return dataframe


def validate_training_dataset(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = [
        "ticker",
        "feature_date",
        "target_date",
        "target_horizon",
        "target_horizon_semantics",
        "target_return_next_5d",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Training Dataset possui "
            "colunas ausentes: "
            f"{missing_columns}"
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "feature_date",
            ]
        ).sum()
    )

    null_required = int(
        dataframe[
            required_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    invalid_date_horizon = int(
        (
            dataframe[
                "target_date"
            ]
            <= dataframe[
                "feature_date"
            ]
        ).sum()
    )

    invalid_target_horizon = int(
        (
            dataframe[
                "target_horizon"
            ]
            != EXPECTED_TARGET_HORIZON
        ).sum()
    )

    invalid_semantics = int(
        (
            dataframe[
                "target_horizon_semantics"
            ]
            != EXPECTED_TARGET_HORIZON_SEMANTICS
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Training Dataset"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"Nulos obrigatórios: "
        f"{null_required:,}"
    )

    print(
        "target_date <= feature_date: "
        f"{invalid_date_horizon:,}"
    )

    print(
        "target_horizon diferente de 5: "
        f"{invalid_target_horizon:,}"
    )

    print(
        "target_horizon_semantics inválida: "
        f"{invalid_semantics:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Training Dataset possui "
            "duplicidades."
        )

    if null_required > 0:
        raise ValueError(
            "Training Dataset possui NULL "
            "em coluna obrigatória."
        )

    if invalid_date_horizon > 0:
        raise ValueError(
            "Training Dataset possui "
            "target_date <= feature_date."
        )

    if invalid_target_horizon > 0:
        raise ValueError(
            "Training Dataset não está "
            "inteiramente em horizonte T+5."
        )

    if invalid_semantics > 0:
        raise ValueError(
            "Training Dataset não está "
            "inteiramente em semântica "
            "GLOBAL_B3_TRADING_DAYS."
        )

    print(
        "\nData Quality aprovada."
    )


def validate_price_quality(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = [
        "ticker",
        "trade_date",
        "ml_quality_status",
        "review_status_on_date",
        "flag_extreme_return",
        "flag_long_gap",
        "flag_possible_microliquidity",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Price Quality possui "
            "colunas ausentes: "
            f"{missing_columns}"
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "trade_date",
            ]
        ).sum()
    )

    invalid_statuses = sorted(
        set(
            dataframe[
                "ml_quality_status"
            ].dropna().unique()
        )
        - {
            "PASS",
            "REVIEW",
        }
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Price Quality"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        "Status inválidos: "
        f"{len(invalid_statuses):,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Price Quality possui "
            "duplicidades."
        )

    if invalid_statuses:
        raise ValueError(
            "Price Quality possui "
            "ml_quality_status inválido: "
            f"{invalid_statuses}"
        )

    print(
        "\nData Quality aprovada."
    )


def build_global_calendar(
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    calendar = (
        price_quality[
            ["trade_date"]
        ]
        .drop_duplicates()
        .sort_values(
            "trade_date"
        )
        .reset_index(
            drop=True
        )
    )

    calendar[
        "global_session_index"
    ] = np.arange(
        len(calendar),
        dtype=np.int64,
    )

    return calendar


def add_global_session_indexes(
    training: pd.DataFrame,
    calendar: pd.DataFrame,
) -> pd.DataFrame:
    result = training.copy()

    feature_calendar = calendar.rename(
        columns={
            "trade_date": "feature_date",
            "global_session_index": (
                "feature_global_session_index"
            ),
        }
    )

    target_calendar = calendar.rename(
        columns={
            "trade_date": "target_date",
            "global_session_index": (
                "target_global_session_index"
            ),
        }
    )

    result = result.merge(
        feature_calendar,
        how="left",
        on="feature_date",
        validate="many_to_one",
    )

    result = result.merge(
        target_calendar,
        how="left",
        on="target_date",
        validate="many_to_one",
    )

    missing_feature_index = int(
        result[
            "feature_global_session_index"
        ]
        .isna()
        .sum()
    )

    missing_target_index = int(
        result[
            "target_global_session_index"
        ]
        .isna()
        .sum()
    )

    if missing_feature_index > 0:
        raise ValueError(
            "Existem feature_dates fora "
            "do calendário global B3."
        )

    if missing_target_index > 0:
        raise ValueError(
            "Existem target_dates fora "
            "do calendário global B3."
        )

    result[
        "target_horizon_sessions"
    ] = (
        result[
            "target_global_session_index"
        ]
        - result[
            "feature_global_session_index"
        ]
    ).astype(
        "int64"
    )

    return result


def build_blocking_signals(
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    result = price_quality.copy()

    result[
        "blocking_price_quality_review"
    ] = (
        result[
            "ml_quality_status"
        ]
        == "REVIEW"
    )

    #
    # REJECTED no registry de corporate
    # actions significa que o evento foi
    # investigado e NÃO é corporate action.
    #
    # Ainda assim ele é relevante para
    # governança / qualidade da amostra.
    #
    result[
        "blocking_rejected_ca_review"
    ] = (
        result[
            "review_status_on_date"
        ]
        == "REJECTED"
    )

    result[
        "blocking_signal"
    ] = (
        result[
            "blocking_price_quality_review"
        ]
        |
        result[
            "blocking_rejected_ca_review"
        ]
    )

    #
    # EXTREME_RETURN isoladamente continua
    # informacional.
    #
    result[
        "informational_extreme_return"
    ] = (
        result[
            "flag_extreme_return"
        ]
        .fillna(
            False
        )
        .astype(
            bool
        )
    )

    return result


def add_feature_window_signals(
    price_quality: pd.DataFrame,
) -> pd.DataFrame:
    result = price_quality.sort_values(
        [
            "ticker",
            "trade_date",
        ]
    ).copy()

    #
    # Mesma semântica das features atuais:
    # janela baseada nas últimas 20
    # observações do próprio ticker.
    #
    result[
        "blocking_feature_window_count"
    ] = (
        result
        .groupby(
            "ticker",
            sort=False,
        )[
            "blocking_signal"
        ]
        .transform(
            lambda series: (
                series
                .astype(
                    "int64"
                )
                .rolling(
                    window=FEATURE_WINDOW_OBSERVATIONS,
                    min_periods=1,
                )
                .sum()
            )
        )
        .astype(
            "int64"
        )
    )

    result[
        "extreme_feature_window_count"
    ] = (
        result
        .groupby(
            "ticker",
            sort=False,
        )[
            "informational_extreme_return"
        ]
        .transform(
            lambda series: (
                series
                .astype(
                    "int64"
                )
                .rolling(
                    window=FEATURE_WINDOW_OBSERVATIONS,
                    min_periods=1,
                )
                .sum()
            )
        )
        .astype(
            "int64"
        )
    )

    result[
        "feature_window_clean"
    ] = (
        result[
            "blocking_feature_window_count"
        ]
        == 0
    )

    return result


def attach_feature_window_signals(
    training: pd.DataFrame,
    quality: pd.DataFrame,
) -> pd.DataFrame:
    feature_columns = [
        "ticker",
        "trade_date",
        "blocking_signal",
        "blocking_price_quality_review",
        "blocking_rejected_ca_review",
        "blocking_feature_window_count",
        "extreme_feature_window_count",
        "feature_window_clean",
    ]

    feature_quality = (
        quality[
            feature_columns
        ]
        .rename(
            columns={
                "trade_date": "feature_date",
                "blocking_signal": (
                    "blocking_signal_on_feature_date"
                ),
                "blocking_price_quality_review": (
                    "price_quality_review_on_feature_date"
                ),
                "blocking_rejected_ca_review": (
                    "rejected_ca_review_on_feature_date"
                ),
            }
        )
    )

    result = training.merge(
        feature_quality,
        how="left",
        on=[
            "ticker",
            "feature_date",
        ],
        validate="one_to_one",
    )

    missing_feature_quality = int(
        result[
            "feature_window_clean"
        ]
        .isna()
        .sum()
    )

    if missing_feature_quality > 0:
        raise ValueError(
            "Existem samples sem Price Quality "
            "na feature_date."
        )

    return result


def build_target_horizon_lookup(
    quality: pd.DataFrame,
    calendar: pd.DataFrame,
) -> pd.DataFrame:
    result = quality.copy()

    calendar_for_quality = (
        calendar.rename(
            columns={
                "global_session_index": (
                    "quality_global_session_index"
                )
            }
        )
    )

    result = result.merge(
        calendar_for_quality,
        how="left",
        on="trade_date",
        validate="many_to_one",
    )

    missing_index = int(
        result[
            "quality_global_session_index"
        ]
        .isna()
        .sum()
    )

    if missing_index > 0:
        raise ValueError(
            "Price Quality possui datas "
            "fora do calendário global."
        )

    result[
        "quality_global_session_index"
    ] = result[
        "quality_global_session_index"
    ].astype(
        "int64"
    )

    return result


def evaluate_target_horizon(
    training: pd.DataFrame,
    quality: pd.DataFrame,
) -> pd.DataFrame:
    result = training.copy()

    blocking_counts: list[int] = []
    extreme_counts: list[int] = []
    review_counts: list[int] = []
    rejected_counts: list[int] = []

    grouped_quality = {
        ticker: group.sort_values(
            "quality_global_session_index"
        )
        for ticker, group
        in quality.groupby(
            "ticker",
            sort=False,
        )
    }

    for row in result.itertuples(
        index=False
    ):
        ticker_quality = (
            grouped_quality.get(
                row.ticker
            )
        )

        if ticker_quality is None:
            raise ValueError(
                "Ticker do Training Dataset "
                "não encontrado em Price Quality: "
                f"{row.ticker}"
            )

        #
        # Target horizon:
        #
        # feature_date NÃO faz parte.
        # target_date faz parte.
        #
        # Exatamente:
        # T+1, T+2, T+3, T+4, T+5.
        #
        horizon = ticker_quality[
            (
                ticker_quality[
                    "quality_global_session_index"
                ]
                > row.feature_global_session_index
            )
            &
            (
                ticker_quality[
                    "quality_global_session_index"
                ]
                <= row.target_global_session_index
            )
        ]

        blocking_counts.append(
            int(
                horizon[
                    "blocking_signal"
                ]
                .sum()
            )
        )

        extreme_counts.append(
            int(
                horizon[
                    "informational_extreme_return"
                ]
                .sum()
            )
        )

        review_counts.append(
            int(
                horizon[
                    "blocking_price_quality_review"
                ]
                .sum()
            )
        )

        rejected_counts.append(
            int(
                horizon[
                    "blocking_rejected_ca_review"
                ]
                .sum()
            )
        )

    result[
        "blocking_target_horizon_count"
    ] = blocking_counts

    result[
        "extreme_target_horizon_count"
    ] = extreme_counts

    result[
        "price_quality_review_target_count"
    ] = review_counts

    result[
        "rejected_ca_review_target_count"
    ] = rejected_counts

    result[
        "target_horizon_clean"
    ] = (
        result[
            "blocking_target_horizon_count"
        ]
        == 0
    )

    return result


def build_ineligibility_reason(
    row: pd.Series,
) -> str:
    reasons: list[str] = []

    if not row[
        "feature_window_clean"
    ]:
        reasons.append(
            "BLOCKING_EVENT_IN_FEATURE_WINDOW"
        )

    if not row[
        "target_horizon_clean"
    ]:
        reasons.append(
            "BLOCKING_EVENT_IN_TARGET_HORIZON"
        )

    if not reasons:
        return "NONE"

    return "|".join(
        reasons
    )


def add_final_eligibility(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result[
        "ml_eligible"
    ] = (
        result[
            "feature_window_clean"
        ]
        &
        result[
            "target_horizon_clean"
        ]
    )

    result[
        "ml_ineligibility_reason"
    ] = result.apply(
        build_ineligibility_reason,
        axis=1,
    )

    result[
        "ml_eligibility_version"
    ] = ML_ELIGIBILITY_VERSION

    result[
        "created_at"
    ] = datetime.now(
        timezone.utc
    )

    return result


def validate_output(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = [
        "ticker",
        "feature_date",
        "target_date",
        "target_horizon",
        "target_horizon_semantics",
        "target_horizon_sessions",
        "feature_window_clean",
        "target_horizon_clean",
        "blocking_feature_window_count",
        "blocking_target_horizon_count",
        "ml_eligible",
        "ml_ineligibility_reason",
        "ml_eligibility_version",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Eligibility possui colunas "
            "ausentes: "
            f"{missing_columns}"
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "feature_date",
            ]
        ).sum()
    )

    null_count = int(
        dataframe[
            required_columns
        ]
        .isna()
        .sum()
        .sum()
    )

    invalid_global_horizon = int(
        (
            dataframe[
                "target_horizon_sessions"
            ]
            != EXPECTED_TARGET_HORIZON
        ).sum()
    )

    invalid_contract_horizon = int(
        (
            dataframe[
                "target_horizon"
            ]
            != EXPECTED_TARGET_HORIZON
        ).sum()
    )

    invalid_semantics = int(
        (
            dataframe[
                "target_horizon_semantics"
            ]
            != EXPECTED_TARGET_HORIZON_SEMANTICS
        ).sum()
    )

    inconsistent_eligible = int(
        (
            dataframe[
                "ml_eligible"
            ]
            != (
                dataframe[
                    "feature_window_clean"
                ]
                &
                dataframe[
                    "target_horizon_clean"
                ]
            )
        ).sum()
    )

    eligible_with_reason = int(
        (
            dataframe[
                "ml_eligible"
            ]
            &
            (
                dataframe[
                    "ml_ineligibility_reason"
                ]
                != "NONE"
            )
        ).sum()
    )

    ineligible_without_reason = int(
        (
            ~dataframe[
                "ml_eligible"
            ]
            &
            (
                dataframe[
                    "ml_ineligibility_reason"
                ]
                == "NONE"
            )
        ).sum()
    )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - ML Eligibility"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Tickers: "
        f"{dataframe['ticker'].nunique():,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"Nulos obrigatórios: "
        f"{null_count:,}"
    )

    print(
        "target_horizon contratual != 5: "
        f"{invalid_contract_horizon:,}"
    )

    print(
        "target_horizon_semantics inválida: "
        f"{invalid_semantics:,}"
    )

    print(
        "Horizonte calculado diferente "
        f"de T+5 global B3: "
        f"{invalid_global_horizon:,}"
    )

    print(
        "Inconsistências ml_eligible: "
        f"{inconsistent_eligible:,}"
    )

    print(
        "Eligible com motivo de bloqueio: "
        f"{eligible_with_reason:,}"
    )

    print(
        "Ineligible sem motivo: "
        f"{ineligible_without_reason:,}"
    )

    if duplicate_count > 0:
        raise ValueError(
            "Eligibility possui duplicidades."
        )

    if null_count > 0:
        raise ValueError(
            "Eligibility possui NULL "
            "em campo obrigatório."
        )

    if invalid_contract_horizon > 0:
        raise ValueError(
            "Contrato de target_horizon "
            "não é T+5."
        )

    if invalid_semantics > 0:
        raise ValueError(
            "Contrato de target não usa "
            "GLOBAL_B3_TRADING_DAYS."
        )

    if invalid_global_horizon > 0:
        raise ValueError(
            "Eligibility encontrou target "
            "fora da semântica global B3 T+5."
        )

    if inconsistent_eligible > 0:
        raise ValueError(
            "Eligibility possui status "
            "inconsistente."
        )

    if eligible_with_reason > 0:
        raise ValueError(
            "Existem samples eligible "
            "com motivo de inelegibilidade."
        )

    if ineligible_without_reason > 0:
        raise ValueError(
            "Existem samples ineligible "
            "sem motivo registrado."
        )

    print(
        "\nData Quality aprovada."
    )


def print_summary(
    dataframe: pd.DataFrame,
) -> None:
    print(
        "\n======================================"
    )
    print(
        "Resumo - FII ML Eligibility"
    )
    print(
        "======================================"
    )

    print(
        f"Version: "
        f"{ML_ELIGIBILITY_VERSION}"
    )

    print(
        f"Samples: "
        f"{len(dataframe):,}"
    )

    eligible_count = int(
        dataframe[
            "ml_eligible"
        ].sum()
    )

    ineligible_count = int(
        (
            ~dataframe[
                "ml_eligible"
            ]
        ).sum()
    )

    print(
        f"ML eligible: "
        f"{eligible_count:,}"
    )

    print(
        f"ML ineligible: "
        f"{ineligible_count:,}"
    )

    if len(dataframe) > 0:
        print(
            "Eligibility rate: "
            f"{eligible_count / len(dataframe) * 100:.2f}%"
        )

    feature_contaminated = int(
        (
            ~dataframe[
                "feature_window_clean"
            ]
        ).sum()
    )

    target_contaminated = int(
        (
            ~dataframe[
                "target_horizon_clean"
            ]
        ).sum()
    )

    both_contaminated = int(
        (
            ~dataframe[
                "feature_window_clean"
            ]
            &
            ~dataframe[
                "target_horizon_clean"
            ]
        ).sum()
    )

    print(
        "\nContaminação temporal:"
    )

    print(
        "  Feature window contaminada: "
        f"{feature_contaminated:,}"
    )

    print(
        "  Target horizon contaminado: "
        f"{target_contaminated:,}"
    )

    print(
        "  Ambos: "
        f"{both_contaminated:,}"
    )

    print(
        "\nMotivos:"
    )

    for value, count in (
        dataframe[
            "ml_ineligibility_reason"
        ]
        .value_counts()
        .items()
    ):
        print(
            f"  {value}: "
            f"{count:,}"
        )

    print(
        "\nSinais informacionais:"
    )

    feature_extreme_samples = int(
        (
            dataframe[
                "extreme_feature_window_count"
            ]
            > 0
        ).sum()
    )

    target_extreme_samples = int(
        (
            dataframe[
                "extreme_target_horizon_count"
            ]
            > 0
        ).sum()
    )

    print(
        "  EXTREME_RETURN na feature window: "
        f"{feature_extreme_samples:,}"
    )

    print(
        "  EXTREME_RETURN no target horizon: "
        f"{target_extreme_samples:,}"
    )

    rejected_feature_samples = int(
        dataframe[
            "rejected_ca_review_on_feature_date"
        ].sum()
    )

    rejected_target_samples = int(
        (
            dataframe[
                "rejected_ca_review_target_count"
            ]
            > 0
        ).sum()
    )

    print(
        "  REJECTED CA na feature_date: "
        f"{rejected_feature_samples:,}"
    )

    print(
        "  REJECTED CA no target horizon: "
        f"{rejected_target_samples:,}"
    )

    ineligible = dataframe[
        ~dataframe[
            "ml_eligible"
        ]
    ].copy()

    print(
        "\n======================================"
    )
    print(
        "Amostra - ML INELIGIBLE"
    )
    print(
        "======================================"
    )

    if ineligible.empty:
        print(
            "Nenhuma amostra inelegível."
        )

    else:
        display = ineligible[
            [
                "ticker",
                "feature_date",
                "target_date",
                "blocking_feature_window_count",
                "blocking_target_horizon_count",
                "extreme_feature_window_count",
                "extreme_target_horizon_count",
                "ml_ineligibility_reason",
            ]
        ].copy()

        display = display.sort_values(
            [
                "feature_date",
                "ticker",
            ]
        )

        print(
            display.head(
                50
            ).to_string(
                index=False
            )
        )

    print(
        "\nArquivo:"
    )

    print(
        OUTPUT_PATH
    )


def select_output_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "ticker",
        "feature_date",
        "target_date",

        "target_horizon",
        "target_horizon_semantics",

        "feature_global_session_index",
        "target_global_session_index",
        "target_horizon_sessions",

        "blocking_signal_on_feature_date",
        "price_quality_review_on_feature_date",
        "rejected_ca_review_on_feature_date",

        "blocking_feature_window_count",
        "extreme_feature_window_count",
        "feature_window_clean",

        "blocking_target_horizon_count",
        "extreme_target_horizon_count",
        "price_quality_review_target_count",
        "rejected_ca_review_target_count",
        "target_horizon_clean",

        "ml_eligible",
        "ml_ineligibility_reason",

        "ml_eligibility_version",
        "created_at",
    ]

    return dataframe[
        columns
    ].copy()


def main() -> None:
    print(
        "Construindo FII ML Eligibility..."
    )

    print(
        f"Version: "
        f"{ML_ELIGIBILITY_VERSION}"
    )

    print(
        "Feature window: "
        f"{FEATURE_WINDOW_OBSERVATIONS} "
        "observações do próprio ticker"
    )

    print(
        "Target horizon: "
        "GLOBAL_B3_TRADING_DAYS T+5"
    )

    training = (
        load_training_dataset()
    )

    training = (
        normalize_training_schema(
            training
        )
    )

    validate_training_dataset(
        training
    )

    quality = (
        load_price_quality()
    )

    validate_price_quality(
        quality
    )

    calendar = (
        build_global_calendar(
            quality
        )
    )

    training = (
        add_global_session_indexes(
            training=training,
            calendar=calendar,
        )
    )

    quality = (
        build_blocking_signals(
            quality
        )
    )

    quality = (
        add_feature_window_signals(
            quality
        )
    )

    training = (
        attach_feature_window_signals(
            training=training,
            quality=quality,
        )
    )

    quality_with_calendar = (
        build_target_horizon_lookup(
            quality=quality,
            calendar=calendar,
        )
    )

    training = (
        evaluate_target_horizon(
            training=training,
            quality=quality_with_calendar,
        )
    )

    training = (
        add_final_eligibility(
            training
        )
    )

    validate_output(
        training
    )

    output = (
        select_output_columns(
            training
        )
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print_summary(
        output
    )

    print(
        "\nCamada criada com sucesso."
    )

    print(
        "Nenhuma sample foi removida."
    )

    print(
        "EXTREME_RETURN sozinho permanece "
        "informacional e não bloqueante."
    )

    print(
        "Corporate Actions CONFIRMED já "
        "foram economicamente ajustados "
        "e não bloqueiam automaticamente."
    )

    print(
        "Corporate Action REJECTED significa "
        "investigado e direcionado ao domínio "
        "de qualidade."
    )


if __name__ == "__main__":
    main()