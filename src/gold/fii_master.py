from __future__ import annotations

import re
import unicodedata

import pandas as pd


FII_CLASS_TYPE = "Classes de Cotas de Fundos FII"

PRIMARY_INSTRUMENT_TYPE = "EqtyInf"
PRIMARY_SECURITY_CATEGORY = "6"
PRIMARY_B3_MARKET = "10"
PRIMARY_B3_SEGMENT = "1"
PRIMARY_TICKER_SUFFIX = "11"


GENERIC_NAME_TOKENS = {
    "FII",
    "FUNDO",
    "FDO",
    "INVESTIMENTO",
    "INV",
    "IMOBILIARIO",
    "IMOB",
    "DE",
    "DA",
    "DO",
    "DAS",
    "DOS",
    "RESPONSABILIDADE",
    "RESP",
    "LIMITADA",
    "LIM",
    "RESPLIM",
}


def normalize_text(
    value: object,
) -> str:
    if pd.isna(value):
        return ""

    text = str(value)

    text = (
        unicodedata.normalize(
            "NFKD",
            text,
        )
        .encode(
            "ascii",
            "ignore",
        )
        .decode("ascii")
        .upper()
    )

    text = re.sub(
        r"[^A-Z0-9]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def build_core_name(
    value: object,
) -> str:
    normalized = normalize_text(
        value
    )

    tokens = [
        token
        for token in normalized.split()
        if token
        not in GENERIC_NAME_TOKENS
    ]

    return " ".join(
        tokens
    )


def _normalize_string_series(
    series: pd.Series,
) -> pd.Series:
    return (
        series
        .astype("string")
        .str.strip()
    )


def prepare_cvm_fii(
    cvm: pd.DataFrame,
) -> pd.DataFrame:
    required_columns = {
        "CNPJ_Classe",
        "Codigo_CVM",
        "Denominacao_Social",
        "Tipo_Classe",
        "Situacao",
    }

    missing_columns = (
        required_columns
        - set(cvm.columns)
    )

    if missing_columns:
        raise ValueError(
            "CVM dataframe is missing "
            "required columns: "
            f"{sorted(missing_columns)}"
        )

    fii = cvm[
        cvm["Tipo_Classe"].eq(
            FII_CLASS_TYPE
        )
    ].copy()

    fii["CNPJ_Classe"] = (
        _normalize_string_series(
            fii["CNPJ_Classe"]
        )
    )

    fii["Codigo_CVM"] = (
        _normalize_string_series(
            fii["Codigo_CVM"]
        )
    )

    fii["core_name"] = (
        fii[
            "Denominacao_Social"
        ]
        .map(
            build_core_name
        )
    )

    fii = fii[
        fii["core_name"].ne("")
    ].copy()

    return fii


def prepare_b3_instruments(
    instruments: pd.DataFrame,
) -> pd.DataFrame:
    required_columns = {
        "instrument_id",
        "instrument_id_type",
        "listing_market",
        "ticker",
        "isin",
        "asset",
        "corporate_name",
        "security_category",
        "b3_market",
        "b3_segment",
        "instrument_type",
        "underlying_instrument_id",
        "report_date",
    }

    missing_columns = (
        required_columns
        - set(instruments.columns)
    )

    if missing_columns:
        raise ValueError(
            "B3 instruments dataframe "
            "is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    result = instruments.copy()

    string_columns = [
        "instrument_id",
        "instrument_id_type",
        "listing_market",
        "ticker",
        "isin",
        "asset",
        "corporate_name",
        "security_category",
        "b3_market",
        "b3_segment",
        "instrument_type",
        "underlying_instrument_id",
    ]

    for column in string_columns:
        result[column] = (
            _normalize_string_series(
                result[column]
            )
        )

    result["core_name"] = (
        result[
            "corporate_name"
        ]
        .map(
            build_core_name
        )
    )

    result = result[
        result["core_name"].ne("")
    ].copy()

    return result


def build_exact_name_bridge(
    cvm_fii: pd.DataFrame,
    instruments: pd.DataFrame,
) -> pd.DataFrame:
    cvm_core_summary = (
        cvm_fii
        .groupby(
            "core_name",
            as_index=False,
        )
        .agg(
            cvm_cnpjs=(
                "CNPJ_Classe",
                "nunique",
            ),
        )
    )

    unique_cvm_core_names = set(
        cvm_core_summary.loc[
            cvm_core_summary[
                "cvm_cnpjs"
            ].eq(1),
            "core_name",
        ]
    )

    cvm_unique = (
        cvm_fii[
            cvm_fii[
                "core_name"
            ].isin(
                unique_cvm_core_names
            )
        ][
            [
                "CNPJ_Classe",
                "Codigo_CVM",
                "Denominacao_Social",
                "Situacao",
                "core_name",
            ]
        ]
        .drop_duplicates(
            subset=[
                "CNPJ_Classe",
                "core_name",
            ]
        )
    )

    bridge = (
        instruments.merge(
            cvm_unique,
            on="core_name",
            how="inner",
        )
    )

    bridge = (
        bridge
        .drop_duplicates(
            subset=[
                "instrument_id",
                "CNPJ_Classe",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return bridge


def mark_resolution_evidence(
    bridge: pd.DataFrame,
    instruments: pd.DataFrame,
    trades: pd.DataFrame | None,
) -> pd.DataFrame:
    result = bridge.copy()

    global_underlying_ids = set(
        instruments[
            "underlying_instrument_id"
        ]
        .dropna()
        .astype(str)
    )

    result[
        "is_underlying_target"
    ] = (
        result[
            "instrument_id"
        ]
        .astype(str)
        .isin(
            global_underlying_ids
        )
    )

    result[
        "matches_primary_signature"
    ] = (
        result[
            "instrument_type"
        ].eq(
            PRIMARY_INSTRUMENT_TYPE
        )
        & result[
            "security_category"
        ].eq(
            PRIMARY_SECURITY_CATEGORY
        )
        & result[
            "b3_market"
        ].eq(
            PRIMARY_B3_MARKET
        )
        & result[
            "b3_segment"
        ].eq(
            PRIMARY_B3_SEGMENT
        )
        & result[
            "ticker"
        ]
        .fillna("")
        .str.endswith(
            PRIMARY_TICKER_SUFFIX
        )
    )

    if trades is None:
        result["is_traded"] = False
        return result

    if "instrument_id" not in trades.columns:
        raise ValueError(
            "B3 trades dataframe "
            "is missing required column: "
            "instrument_id"
        )

    traded_ids = set(
        trades[
            "instrument_id"
        ]
        .dropna()
        .astype(str)
    )

    result["is_traded"] = (
        result[
            "instrument_id"
        ]
        .astype(str)
        .isin(
            traded_ids
        )
    )

    return result


def resolve_primary_instrument(
    group: pd.DataFrame,
) -> dict[str, object]:
    structural_candidates = (
        group[
            group[
                "is_underlying_target"
            ]
        ]
        .drop_duplicates(
            subset=[
                "instrument_id",
            ]
        )
    )

    if len(
        structural_candidates
    ) == 1:
        selected = (
            structural_candidates
            .iloc[0]
        )

        evidence = (
            "STRUCTURAL_AND_TRADED"
            if bool(
                selected[
                    "is_traded"
                ]
            )
            else "STRUCTURAL_ONLY"
        )

        return {
            "primary_instrument_id":
                selected[
                    "instrument_id"
                ],
            "ticker":
                selected[
                    "ticker"
                ],
            "isin":
                selected[
                    "isin"
                ],
            "instrument_id_type":
                selected[
                    "instrument_id_type"
                ],
            "listing_market":
                selected[
                    "listing_market"
                ],
            "asset":
                selected[
                    "asset"
                ],
            "corporate_name":
                selected[
                    "corporate_name"
                ],
            "resolution_method":
                "B3_UNDERLYING_REFERENCE",
            "resolution_status":
                "AUTO_RESOLVED",
            "resolution_evidence":
                evidence,
        }

    signature_candidates = (
        group[
            group[
                "matches_primary_signature"
            ]
        ]
        .drop_duplicates(
            subset=[
                "instrument_id",
            ]
        )
    )

    if (
        len(
            structural_candidates
        ) == 0
        and len(
            signature_candidates
        ) == 1
    ):
        selected = (
            signature_candidates
            .iloc[0]
        )

        evidence = (
            "SIGNATURE_AND_TRADED"
            if bool(
                selected[
                    "is_traded"
                ]
            )
            else "SIGNATURE_ONLY"
        )

        return {
            "primary_instrument_id":
                selected[
                    "instrument_id"
                ],
            "ticker":
                selected[
                    "ticker"
                ],
            "isin":
                selected[
                    "isin"
                ],
            "instrument_id_type":
                selected[
                    "instrument_id_type"
                ],
            "listing_market":
                selected[
                    "listing_market"
                ],
            "asset":
                selected[
                    "asset"
                ],
            "corporate_name":
                selected[
                    "corporate_name"
                ],
            "resolution_method":
                "B3_PRIMARY_SIGNATURE",
            "resolution_status":
                "AUTO_RESOLVED",
            "resolution_evidence":
                evidence,
        }

    return {
        "primary_instrument_id":
            pd.NA,
        "ticker":
            pd.NA,
        "isin":
            pd.NA,
        "instrument_id_type":
            pd.NA,
        "listing_market":
            pd.NA,
        "asset":
            pd.NA,
        "corporate_name":
            pd.NA,
        "resolution_method":
            pd.NA,
        "resolution_status":
            "UNRESOLVED",
        "resolution_evidence":
            pd.NA,
    }


def build_fii_master(
    cvm: pd.DataFrame,
    instruments: pd.DataFrame,
    trades: pd.DataFrame | None = None,
) -> pd.DataFrame:
    cvm_fii = prepare_cvm_fii(
        cvm
    )

    b3_instruments = (
        prepare_b3_instruments(
            instruments
        )
    )

    bridge = build_exact_name_bridge(
        cvm_fii=cvm_fii,
        instruments=b3_instruments,
    )

    bridge = mark_resolution_evidence(
        bridge=bridge,
        instruments=b3_instruments,
        trades=trades,
    )

    records: list[
        dict[str, object]
    ] = []

    for (
        cnpj_classe,
        group,
    ) in bridge.groupby(
        "CNPJ_Classe",
        sort=True,
    ):
        cvm_row = group.iloc[0]

        resolution = (
            resolve_primary_instrument(
                group
            )
        )

        record = {
            "cnpj_classe":
                cnpj_classe,
            "codigo_cvm":
                cvm_row[
                    "Codigo_CVM"
                ],
            "denominacao_social":
                cvm_row[
                    "Denominacao_Social"
                ],
            "situacao_cvm":
                cvm_row[
                    "Situacao"
                ],
            "core_name":
                cvm_row[
                    "core_name"
                ],
            **resolution,
        }

        records.append(
            record
        )

    fii_master = pd.DataFrame(
        records
    )

    if fii_master.empty:
        return fii_master

    report_dates = (
        b3_instruments[
            "report_date"
        ]
        .dropna()
    )

    if not report_dates.empty:
        fii_master[
            "reference_date"
        ] = report_dates.max()
    else:
        fii_master[
            "reference_date"
        ] = pd.NaT

    fii_master[
        "cnpj_classe"
    ] = (
        fii_master[
            "cnpj_classe"
        ]
        .astype("string")
    )

    fii_master[
        "codigo_cvm"
    ] = (
        fii_master[
            "codigo_cvm"
        ]
        .astype("string")
    )

    string_columns = [
        "primary_instrument_id",
        "ticker",
        "isin",
        "instrument_id_type",
        "listing_market",
        "asset",
        "corporate_name",
        "resolution_method",
        "resolution_status",
        "resolution_evidence",
    ]

    for column in string_columns:
        fii_master[column] = (
            fii_master[column]
            .astype("string")
        )

    return (
        fii_master
        .sort_values(
            [
                "resolution_status",
                "ticker",
                "cnpj_classe",
            ],
            na_position="last",
        )
        .reset_index(
            drop=True
        )
    )