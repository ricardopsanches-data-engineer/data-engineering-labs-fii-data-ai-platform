from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REGISTRY_PATH = (
    PROJECT_ROOT
    / "config"
    / "corporate_actions"
    / "fii_corporate_action_reviews.csv"
)

BACKUP_DIR = (
    PROJECT_ROOT
    / "config"
    / "corporate_actions"
    / "backups"
)


EXPECTED_ROW_COUNT = 79
EXPECTED_CONFIRMED_COUNT = 16


LEGACY_COLUMNS = [
    "ticker",
    "event_date",
    "review_status",
    "event_type",
    "quantity_multiplier",
    "price_adjustment_factor",
    "cash_amount_per_unit",
    "confirmation_source",
    "confirmation_date",
    "review_notes",
]


REGISTRY_V2_COLUMNS = [
    "ticker",
    "event_date",
    "review_status",
    "event_type",

    "quantity_multiplier",
    "price_adjustment_factor",

    "cash_amount_per_unit",
    "in_kind_amount_per_unit",
    "total_economic_value_per_unit",
    "in_kind_asset_ticker",
    "in_kind_quantity_per_unit",

    "corporate_action_record_date",
    "corporate_action_effective_date",
    "cash_payment_date",
    "in_kind_delivery_date",
    "first_post_event_trade_date",

    "confirmation_source",
    "confirmation_date",
    "governance_review_date",
    "review_notes",
]


STRUCTURAL_EVENT_TYPES = {
    "SPLIT",
    "REVERSE_SPLIT",
}

ECONOMIC_EVENT_TYPES = {
    "AMORTIZATION",
}


#
# Overrides governados dos 16 Corporate Actions CONFIRMED.
#
# Regra:
# - somente dados que já levantamos/documentamos
#   são preenchidos;
# - datas desconhecidas permanecem vazias;
# - event_date continua representando a data
#   detectada na série de preços;
# - first_post_event_trade_date explicita essa
#   semântica para os eventos confirmados.
#
CONFIRMED_OVERRIDES: dict[
    tuple[str, str],
    dict[str, object],
] = {
    #
    # ==========================================================
    # STRUCTURAL EVENTS
    # ==========================================================
    #

    (
        "TEPP11",
        "2025-11-28",
    ): {
        "corporate_action_record_date": "2025-11-27",
        "corporate_action_effective_date": "2025-11-28",
        "first_post_event_trade_date": "2025-11-28",
    },

    (
        "ZAVI11",
        "2025-12-11",
    ): {
        "corporate_action_record_date": "2025-12-10",
        "corporate_action_effective_date": "2025-12-11",
        "first_post_event_trade_date": "2025-12-11",
    },

    (
        "CARE11",
        "2026-02-10",
    ): {
        #
        # A AGE e o prazo operacional estão documentados,
        # mas não vamos inventar uma record_date.
        #
        "corporate_action_effective_date": "2026-02-10",
        "first_post_event_trade_date": "2026-02-10",
    },

    (
        "SJAU11",
        "2026-03-24",
    ): {
        "corporate_action_effective_date": "2026-03-24",
        "first_post_event_trade_date": "2026-03-24",
    },

    (
        "VVRI11",
        "2026-07-16",
    ): {
        "corporate_action_record_date": "2026-07-15",
        "corporate_action_effective_date": "2026-07-16",
        "first_post_event_trade_date": "2026-07-16",
    },

    #
    # ==========================================================
    # CASH-ONLY AMORTIZATIONS
    # ==========================================================
    #

    (
        "WSEC11",
        "2025-10-09",
    ): {
        #
        # O disclosure foi anunciado em 08/10,
        # mas não vamos converter announcement date
        # artificialmente em record_date.
        #
        "corporate_action_effective_date": "2025-10-09",
        "cash_payment_date": "2025-10-24",
        "first_post_event_trade_date": "2025-10-09",
    },

    (
        "FMOF11",
        "2025-10-20",
    ): {
        "corporate_action_record_date": "2025-10-17",
        "corporate_action_effective_date": "2025-10-20",
        "cash_payment_date": "2025-11-11",
        "first_post_event_trade_date": "2025-10-20",
    },

    (
        "BRIM11",
        "2026-01-02",
    ): {
        "corporate_action_record_date": "2025-12-30",
        "corporate_action_effective_date": "2026-01-02",
        "cash_payment_date": "2026-01-23",
        "first_post_event_trade_date": "2026-01-02",
    },

    (
        "HDEL11",
        "2026-04-09",
    ): {
        "corporate_action_record_date": "2026-04-07",
        "corporate_action_effective_date": "2026-04-09",
        "first_post_event_trade_date": "2026-04-09",
    },

    (
        "CYLD11",
        "2026-04-13",
    ): {
        "corporate_action_record_date": "2026-04-09",
        "corporate_action_effective_date": "2026-04-13",
        "cash_payment_date": "2026-05-08",
        "first_post_event_trade_date": "2026-04-13",
    },

    (
        "RBLG11",
        "2026-04-20",
    ): {
        "corporate_action_record_date": "2026-03-16",
        "corporate_action_effective_date": "2026-04-20",
        "cash_payment_date": "2026-04-24",
        "first_post_event_trade_date": "2026-04-20",
    },

    (
        "PNDL11",
        "2026-05-11",
    ): {
        "corporate_action_record_date": "2026-03-19",

        #
        # O efeito econômico ocorreu anteriormente,
        # mas o primeiro preço pós-evento observável
        # na Silver foi apenas em 11/05.
        #
        # Para esta Fase 0, effective_date permanece
        # alinhada à primeira observação de mercado
        # usada pelo retorno econômico.
        #
        "corporate_action_effective_date": "2026-05-11",
        "cash_payment_date": "2026-04-02",
        "first_post_event_trade_date": "2026-05-11",
    },

    (
        "PNDL11",
        "2026-05-18",
    ): {
        "corporate_action_record_date": "2026-05-11",
        "corporate_action_effective_date": "2026-05-18",
        "cash_payment_date": "2026-05-22",
        "first_post_event_trade_date": "2026-05-18",
    },

    (
        "RDLI11",
        "2026-07-09",
    ): {
        "corporate_action_record_date": "2026-07-08",
        "corporate_action_effective_date": "2026-07-09",
        "first_post_event_trade_date": "2026-07-09",
    },

    (
        "KNPR11",
        "2026-08-03",
    ): {
        "corporate_action_record_date": "2026-07-31",
        "corporate_action_effective_date": "2026-08-03",
        "cash_payment_date": "2026-08-12",
        "first_post_event_trade_date": "2026-08-03",
    },

    #
    # ==========================================================
    # MIXED / IN-KIND AMORTIZATION
    # ==========================================================
    #

    (
        "VIUR11",
        "2026-04-09",
    ): {
        "cash_amount_per_unit": 0.26294411,
        "in_kind_amount_per_unit": 3.52844701,
        "total_economic_value_per_unit": 3.79139112,

        "in_kind_asset_ticker": "TRXF11",
        "in_kind_quantity_per_unit": 0.03881679,

        "corporate_action_record_date": "2026-04-08",
        "corporate_action_effective_date": "2026-04-09",

        "cash_payment_date": "2026-05-28",
        "in_kind_delivery_date": "2026-04-13",

        "first_post_event_trade_date": "2026-04-09",
    },
}


DATE_COLUMNS = [
    "event_date",
    "corporate_action_record_date",
    "corporate_action_effective_date",
    "cash_payment_date",
    "in_kind_delivery_date",
    "first_post_event_trade_date",
    "confirmation_date",
    "governance_review_date",
]


NUMERIC_COLUMNS = [
    "quantity_multiplier",
    "price_adjustment_factor",
    "cash_amount_per_unit",
    "in_kind_amount_per_unit",
    "total_economic_value_per_unit",
    "in_kind_quantity_per_unit",
]


def load_registry() -> pd.DataFrame:
    """
    Carrega o registry legado.
    """

    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(
            "Registry não encontrado: "
            f"{REGISTRY_PATH}"
        )

    dataframe = pd.read_csv(
        REGISTRY_PATH
    )

    print(
        "\n======================================"
    )
    print(
        "Registry atual"
    )
    print(
        "======================================"
    )

    print(
        f"Arquivo: {REGISTRY_PATH}"
    )

    print(
        f"Linhas: {len(dataframe):,}"
    )

    print(
        f"Colunas: {len(dataframe.columns):,}"
    )

    return dataframe


def validate_legacy_contract(
    dataframe: pd.DataFrame,
) -> None:
    """
    Impede migração sobre um arquivo
    inesperado.
    """

    missing_columns = [
        column
        for column in LEGACY_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Registry legado possui colunas "
            "obrigatórias ausentes: "
            f"{missing_columns}"
        )

    if len(dataframe) != EXPECTED_ROW_COUNT:
        raise ValueError(
            "Quantidade inesperada de registros. "
            f"Esperado={EXPECTED_ROW_COUNT}, "
            f"encontrado={len(dataframe)}."
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "event_date",
            ]
        ).sum()
    )

    if duplicate_count > 0:
        raise ValueError(
            "Registry possui decisões duplicadas "
            "por ticker + event_date."
        )

    confirmed_count = int(
        dataframe[
            "review_status"
        ]
        .eq(
            "CONFIRMED"
        )
        .sum()
    )

    if confirmed_count != EXPECTED_CONFIRMED_COUNT:
        raise ValueError(
            "Quantidade de CONFIRMED inesperada. "
            f"Esperado={EXPECTED_CONFIRMED_COUNT}, "
            f"encontrado={confirmed_count}."
        )

    print(
        "\nContrato legado validado."
    )

    print(
        f"CONFIRMED: {confirmed_count:,}"
    )


def normalize_legacy_fields(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza chaves e tipos básicos
    antes da migração.
    """

    result = dataframe.copy()

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

    result[
        "event_date"
    ] = pd.to_datetime(
        result[
            "event_date"
        ],
        errors="raise",
    )

    result[
        "review_status"
    ] = (
        result[
            "review_status"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    result[
        "event_type"
    ] = (
        result[
            "event_type"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    for column in [
        "quantity_multiplier",
        "price_adjustment_factor",
        "cash_amount_per_unit",
    ]:
        result[
            column
        ] = pd.to_numeric(
            result[
                column
            ],
            errors="coerce",
        )

    return result


def add_v2_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adiciona o contrato novo sem
    remover campos legados.
    """

    result = dataframe.copy()

    new_columns_with_default = {
        "in_kind_amount_per_unit": np.nan,
        "total_economic_value_per_unit": np.nan,
        "in_kind_asset_ticker": pd.NA,
        "in_kind_quantity_per_unit": np.nan,

        "corporate_action_record_date": pd.NaT,
        "corporate_action_effective_date": pd.NaT,
        "cash_payment_date": pd.NaT,
        "in_kind_delivery_date": pd.NaT,
        "first_post_event_trade_date": pd.NaT,

        "governance_review_date": pd.NaT,
    }

    for column, default_value in (
        new_columns_with_default.items()
    ):
        if column not in result.columns:
            result[
                column
            ] = default_value

    return result


def populate_generic_confirmed_semantics(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Preenche regras que são verdadeiras
    por construção para os eventos
    confirmados.

    AMORTIZATION cash-only:
        total economic value = cash amount
        in-kind value = 0

    Structural:
        não recebe valor econômico.
    """

    result = dataframe.copy()

    confirmed_mask = (
        result[
            "review_status"
        ]
        .eq(
            "CONFIRMED"
        )
    )

    amortization_mask = (
        confirmed_mask
        &
        result[
            "event_type"
        ]
        .eq(
            "AMORTIZATION"
        )
    )

    result.loc[
        amortization_mask,
        "total_economic_value_per_unit",
    ] = result.loc[
        amortization_mask,
        "cash_amount_per_unit",
    ].astype(float)

    result.loc[
        amortization_mask,
        "in_kind_amount_per_unit",
    ] = 0.0

    #
    # Para todo evento confirmado,
    # event_date é atualmente a data
    # de manifestação detectada na série.
    #
    result.loc[
        confirmed_mask,
        "first_post_event_trade_date",
    ] = result.loc[
        confirmed_mask,
        "event_date",
    ]

    result.loc[
        confirmed_mask,
        "corporate_action_effective_date",
    ] = result.loc[
        confirmed_mask,
        "event_date",
    ]

    return result


def apply_confirmed_overrides(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aplica somente atributos explicitamente
    governados por ticker + event_date.
    """

    result = dataframe.copy()

    applied_keys: set[
        tuple[str, str]
    ] = set()

    for (
        ticker,
        event_date_string,
    ), payload in (
        CONFIRMED_OVERRIDES.items()
    ):
        event_date = pd.Timestamp(
            event_date_string
        )

        mask = (
            result[
                "ticker"
            ].eq(
                ticker
            )
            &
            result[
                "event_date"
            ].eq(
                event_date
            )
        )

        match_count = int(
            mask.sum()
        )

        if match_count != 1:
            raise ValueError(
                "Override governado não encontrou "
                "exatamente uma decisão: "
                f"{ticker} {event_date_string}. "
                f"Matches={match_count}"
            )

        row = result.loc[
            mask
        ].iloc[0]

        if (
            row[
                "review_status"
            ]
            != "CONFIRMED"
        ):
            raise ValueError(
                "Override existe para evento "
                "não CONFIRMED: "
                f"{ticker} {event_date_string}"
            )

        for column, value in (
            payload.items()
        ):
            if column in DATE_COLUMNS:
                value = pd.Timestamp(
                    value
                )

            result.loc[
                mask,
                column,
            ] = value

        applied_keys.add(
            (
                ticker,
                event_date_string,
            )
        )

    confirmed_keys = {
        (
            row.ticker,
            row.event_date.strftime(
                "%Y-%m-%d"
            ),
        )
        for row in result[
            result[
                "review_status"
            ]
            .eq(
                "CONFIRMED"
            )
        ].itertuples(
            index=False
        )
    }

    missing_overrides = (
        confirmed_keys
        - applied_keys
    )

    extra_overrides = (
        applied_keys
        - confirmed_keys
    )

    if missing_overrides:
        raise ValueError(
            "Corporate Actions CONFIRMED sem "
            "override governado: "
            f"{sorted(missing_overrides)}"
        )

    if extra_overrides:
        raise ValueError(
            "Overrides sem Corporate Action "
            "CONFIRMED correspondente: "
            f"{sorted(extra_overrides)}"
        )

    return result


def populate_governance_review_date(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    governance_review_date é um campo novo.

    O histórico legado não possui uma data
    governada confiável para todas as decisões.

    Portanto NÃO copiamos confirmation_date,
    pois ela possui semântica inconsistente.

    O campo permanece vazio nesta migração.
    """

    result = dataframe.copy()

    result[
        "governance_review_date"
    ] = pd.NaT

    return result


def normalize_v2_types(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza tipos do Registry v2.
    """

    result = dataframe.copy()

    for column in DATE_COLUMNS:
        result[
            column
        ] = pd.to_datetime(
            result[
                column
            ],
            errors="coerce",
        )

    for column in NUMERIC_COLUMNS:
        result[
            column
        ] = pd.to_numeric(
            result[
                column
            ],
            errors="coerce",
        )

    result[
        "in_kind_asset_ticker"
    ] = (
        result[
            "in_kind_asset_ticker"
        ]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return result


def validate_registry_v2(
    dataframe: pd.DataFrame,
) -> None:
    """
    Validação forte antes de sobrescrever
    o CSV governado.
    """

    missing_columns = [
        column
        for column in REGISTRY_V2_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "Registry v2 possui colunas "
            "ausentes: "
            f"{missing_columns}"
        )

    if len(dataframe) != EXPECTED_ROW_COUNT:
        raise ValueError(
            "Migração alterou a quantidade "
            "de decisões."
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=[
                "ticker",
                "event_date",
            ]
        ).sum()
    )

    if duplicate_count > 0:
        raise ValueError(
            "Registry v2 possui decisões "
            "duplicadas."
        )

    confirmed = dataframe[
        dataframe[
            "review_status"
        ]
        .eq(
            "CONFIRMED"
        )
    ].copy()

    if (
        len(confirmed)
        != EXPECTED_CONFIRMED_COUNT
    ):
        raise ValueError(
            "Migração alterou a quantidade "
            "de Corporate Actions CONFIRMED."
        )

    unsupported_confirmed_types = sorted(
        set(
            confirmed[
                "event_type"
            ]
            .dropna()
            .tolist()
        )
        - (
            STRUCTURAL_EVENT_TYPES
            | ECONOMIC_EVENT_TYPES
        )
    )

    if unsupported_confirmed_types:
        raise ValueError(
            "Tipos confirmados não "
            "suportados: "
            f"{unsupported_confirmed_types}"
        )

    #
    # ==========================================================
    # STRUCTURAL
    # ==========================================================
    #

    structural = confirmed[
        confirmed[
            "event_type"
        ]
        .isin(
            STRUCTURAL_EVENT_TYPES
        )
    ]

    invalid_structural_factor = (
        structural[
            "price_adjustment_factor"
        ]
        .isna()
        |
        (
            structural[
                "price_adjustment_factor"
            ]
            <= 0
        )
    )

    invalid_structural_quantity = (
        structural[
            "quantity_multiplier"
        ]
        .isna()
        |
        (
            structural[
                "quantity_multiplier"
            ]
            <= 0
        )
    )

    if invalid_structural_factor.any():
        raise ValueError(
            "Structural event sem "
            "price_adjustment_factor válido."
        )

    if invalid_structural_quantity.any():
        raise ValueError(
            "Structural event sem "
            "quantity_multiplier válido."
        )

    structural_product = (
        structural[
            "quantity_multiplier"
        ].astype(float)
        * structural[
            "price_adjustment_factor"
        ].astype(float)
    )

    if (
        ~np.isclose(
            structural_product,
            1.0,
            rtol=0.05,
            atol=0.0,
        )
    ).any():
        raise ValueError(
            "Structural event possui "
            "quantity_multiplier e "
            "price_adjustment_factor "
            "não recíprocos."
        )

    #
    # ==========================================================
    # AMORTIZATION
    # ==========================================================
    #

    amortizations = confirmed[
        confirmed[
            "event_type"
        ]
        .eq(
            "AMORTIZATION"
        )
    ]

    invalid_total_economic_value = (
        amortizations[
            "total_economic_value_per_unit"
        ]
        .isna()
        |
        (
            amortizations[
                "total_economic_value_per_unit"
            ]
            <= 0
        )
    )

    if invalid_total_economic_value.any():
        invalid_rows = amortizations.loc[
            invalid_total_economic_value,
            [
                "ticker",
                "event_date",
                "total_economic_value_per_unit",
            ],
        ]

        raise ValueError(
            "AMORTIZATION sem valor econômico "
            "total válido:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    negative_cash = (
        amortizations[
            "cash_amount_per_unit"
        ]
        .fillna(
            0.0
        )
        < 0
    )

    negative_in_kind = (
        amortizations[
            "in_kind_amount_per_unit"
        ]
        .fillna(
            0.0
        )
        < 0
    )

    if negative_cash.any():
        raise ValueError(
            "AMORTIZATION possui cash negativo."
        )

    if negative_in_kind.any():
        raise ValueError(
            "AMORTIZATION possui in-kind "
            "negativo."
        )

    component_sum = (
        amortizations[
            "cash_amount_per_unit"
        ]
        .fillna(
            0.0
        )
        .astype(float)
        +
        amortizations[
            "in_kind_amount_per_unit"
        ]
        .fillna(
            0.0
        )
        .astype(float)
    )

    total_value = (
        amortizations[
            "total_economic_value_per_unit"
        ]
        .astype(float)
    )

    component_mismatch = (
        ~np.isclose(
            component_sum,
            total_value,
            rtol=1e-8,
            atol=1e-8,
        )
    )

    if component_mismatch.any():
        invalid_rows = amortizations.loc[
            component_mismatch,
            [
                "ticker",
                "event_date",
                "cash_amount_per_unit",
                "in_kind_amount_per_unit",
                "total_economic_value_per_unit",
            ],
        ]

        raise ValueError(
            "Componentes econômicos não "
            "fecham com o valor total:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    #
    # ==========================================================
    # IN-KIND CONTRACT
    # ==========================================================
    #

    in_kind_events = amortizations[
        amortizations[
            "in_kind_amount_per_unit"
        ]
        .fillna(
            0.0
        )
        .gt(
            0.0
        )
    ]

    missing_in_kind_ticker = (
        in_kind_events[
            "in_kind_asset_ticker"
        ]
        .isna()
    )

    missing_in_kind_quantity = (
        in_kind_events[
            "in_kind_quantity_per_unit"
        ]
        .isna()
        |
        (
            in_kind_events[
                "in_kind_quantity_per_unit"
            ]
            <= 0
        )
    )

    if missing_in_kind_ticker.any():
        raise ValueError(
            "Evento in-kind sem "
            "in_kind_asset_ticker."
        )

    if missing_in_kind_quantity.any():
        raise ValueError(
            "Evento in-kind sem quantidade "
            "válida do ativo recebido."
        )

    #
    # ==========================================================
    # DATE SEMANTICS
    # ==========================================================
    #

    missing_first_post_trade = (
        confirmed[
            "first_post_event_trade_date"
        ]
        .isna()
    )

    if missing_first_post_trade.any():
        raise ValueError(
            "Corporate Action CONFIRMED sem "
            "first_post_event_trade_date."
        )

    detector_date_mismatch = (
        confirmed[
            "event_date"
        ]
        != confirmed[
            "first_post_event_trade_date"
        ]
    )

    if detector_date_mismatch.any():
        invalid_rows = confirmed.loc[
            detector_date_mismatch,
            [
                "ticker",
                "event_date",
                "first_post_event_trade_date",
            ],
        ]

        raise ValueError(
            "Contrato atual exige "
            "event_date == "
            "first_post_event_trade_date:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    record_date_after_trade = (
        confirmed[
            "corporate_action_record_date"
        ]
        .notna()
        &
        (
            confirmed[
                "corporate_action_record_date"
            ]
            >
            confirmed[
                "first_post_event_trade_date"
            ]
        )
    )

    if record_date_after_trade.any():
        invalid_rows = confirmed.loc[
            record_date_after_trade,
            [
                "ticker",
                "event_date",
                "corporate_action_record_date",
                "first_post_event_trade_date",
            ],
        ]

        raise ValueError(
            "record_date posterior ao primeiro "
            "trade pós-evento:\n"
            f"{invalid_rows.to_string(index=False)}"
        )

    #
    # ==========================================================
    # VIUR11 SPECIAL ASSERTIONS
    # ==========================================================
    #

    viur = confirmed[
        confirmed[
            "ticker"
        ]
        .eq(
            "VIUR11"
        )
        &
        confirmed[
            "event_date"
        ]
        .eq(
            pd.Timestamp(
                "2026-04-09"
            )
        )
    ]

    if len(viur) != 1:
        raise ValueError(
            "VIUR11 governado não encontrado "
            "exatamente uma vez."
        )

    viur_row = viur.iloc[0]

    if (
        viur_row[
            "in_kind_asset_ticker"
        ]
        != "TRXF11"
    ):
        raise ValueError(
            "VIUR11 deveria possuir "
            "TRXF11 como ativo in-kind."
        )

    #
    # ==========================================================
    # LEGACY FIELD PRESERVATION
    # ==========================================================
    #

    required_legacy_non_null = [
        "ticker",
        "event_date",
        "review_status",
        "event_type",
        "confirmation_source",
        "review_notes",
    ]

    legacy_null_count = int(
        dataframe[
            required_legacy_non_null
        ]
        .isna()
        .sum()
        .sum()
    )

    if legacy_null_count > 0:
        raise ValueError(
            "Migração introduziu nulos "
            "em campos legados obrigatórios."
        )

    print(
        "\n======================================"
    )
    print(
        "Data Quality - Registry v2"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas: "
        f"{len(dataframe):,}"
    )

    print(
        f"Colunas: "
        f"{len(REGISTRY_V2_COLUMNS):,}"
    )

    print(
        f"Duplicidades: "
        f"{duplicate_count:,}"
    )

    print(
        f"CONFIRMED: "
        f"{len(confirmed):,}"
    )

    print(
        "Structural events: "
        f"{len(structural):,}"
    )

    print(
        "Amortizations: "
        f"{len(amortizations):,}"
    )

    print(
        "Eventos com componente in-kind: "
        f"{len(in_kind_events):,}"
    )

    print(
        "\nData Quality aprovada."
    )


def select_v2_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Define ordem física final do CSV.
    """

    return dataframe[
        REGISTRY_V2_COLUMNS
    ].copy()


def print_confirmed_summary(
    dataframe: pd.DataFrame,
) -> None:
    confirmed = dataframe[
        dataframe[
            "review_status"
        ]
        .eq(
            "CONFIRMED"
        )
    ].copy()

    display_columns = [
        "ticker",
        "event_date",
        "event_type",

        "quantity_multiplier",
        "price_adjustment_factor",

        "cash_amount_per_unit",
        "in_kind_amount_per_unit",
        "total_economic_value_per_unit",

        "in_kind_asset_ticker",
        "in_kind_quantity_per_unit",

        "corporate_action_record_date",
        "corporate_action_effective_date",
        "cash_payment_date",
        "in_kind_delivery_date",
        "first_post_event_trade_date",
    ]

    print(
        "\n======================================"
    )
    print(
        "Corporate Actions CONFIRMED - v2"
    )
    print(
        "======================================"
    )

    print(
        confirmed[
            display_columns
        ]
        .sort_values(
            [
                "event_date",
                "ticker",
            ]
        )
        .to_string(
            index=False
        )
    )


def create_backup() -> Path:
    """
    Cria cópia do CSV original antes
    de qualquer sobrescrita.
    """

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_path = (
        BACKUP_DIR
        / (
            "fii_corporate_action_reviews"
            f"_pre_registry_v2_{timestamp}.csv"
        )
    )

    shutil.copy2(
        REGISTRY_PATH,
        backup_path,
    )

    return backup_path


def write_registry(
    dataframe: pd.DataFrame,
) -> Path:
    """
    Sobrescreve o registry somente depois
    de todas as validações.
    """

    backup_path = create_backup()

    dataframe.to_csv(
        REGISTRY_PATH,
        index=False,
        date_format="%Y-%m-%d",
    )

    return backup_path


def main() -> None:
    print(
        "Migrando Governed Corporate Action "
        "Registry para v2..."
    )

    registry = load_registry()

    validate_legacy_contract(
        registry
    )

    migrated = normalize_legacy_fields(
        registry
    )

    migrated = add_v2_columns(
        migrated
    )

    migrated = (
        populate_generic_confirmed_semantics(
            migrated
        )
    )

    migrated = apply_confirmed_overrides(
        migrated
    )

    migrated = populate_governance_review_date(
        migrated
    )

    migrated = normalize_v2_types(
        migrated
    )

    migrated = select_v2_columns(
        migrated
    )

    validate_registry_v2(
        migrated
    )

    print_confirmed_summary(
        migrated
    )

    backup_path = write_registry(
        migrated
    )

    print(
        "\n======================================"
    )
    print(
        "Migração concluída"
    )
    print(
        "======================================"
    )

    print(
        f"Registry v2: "
        f"{REGISTRY_PATH}"
    )

    print(
        f"Backup do registry anterior: "
        f"{backup_path}"
    )

    print(
        f"Linhas preservadas: "
        f"{len(migrated):,}"
    )

    print(
        f"Colunas finais: "
        f"{len(migrated.columns):,}"
    )

    print(
        "\nNenhuma decisão de review foi "
        "criada ou removida."
    )

    print(
        "CONFIRMED / REJECTED / "
        "NOT_APPLICABLE foram preservados."
    )

    print(
        "confirmation_date foi preservada "
        "como campo legado."
    )

    print(
        "governance_review_date permanece "
        "vazia quando o histórico não possui "
        "uma data governada confiável."
    )

    print(
        "VIUR11 agora separa corretamente "
        "cash e distribuição in-kind."
    )


if __name__ == "__main__":
    main()