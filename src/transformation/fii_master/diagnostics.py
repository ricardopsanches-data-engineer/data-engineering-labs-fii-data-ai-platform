from __future__ import annotations

from builder import (
    DEFAULT_CVM_RAW_DIR,
    DEFAULT_FUNDS_EXPLORER_BRONZE_DIR,
    find_latest_file,
    load_cvm_fii_classes,
    load_funds_explorer_mapping,
)


def main() -> None:
    print(
        "Diagnóstico de cardinalidade "
        "do FII Master..."
    )

    cvm_zip_path = find_latest_file(
        base_directory=DEFAULT_CVM_RAW_DIR,
        filename="registro_fundo_classe.zip",
    )

    funds_explorer_mapping_path = (
        find_latest_file(
            base_directory=(
                DEFAULT_FUNDS_EXPLORER_BRONZE_DIR
            ),
            filename="ticker_cnpj_mapping.csv",
        )
    )

    cvm = load_cvm_fii_classes(
        cvm_zip_path
    )

    funds = load_funds_explorer_mapping(
        funds_explorer_mapping_path
    )

    # -----------------------------------------
    # 1. CNPJs duplicados na CVM
    # -----------------------------------------

    cvm_duplicates = cvm[
        cvm["cnpj"].duplicated(
            keep=False
        )
    ].copy()

    cvm_duplicates = (
        cvm_duplicates.sort_values(
            by="cnpj"
        )
    )

    print(
        "\n======================================"
    )
    print(
        "CNPJs duplicados na CVM"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas envolvidas: "
        f"{len(cvm_duplicates):,}"
    )

    print(
        f"CNPJs envolvidos: "
        f"{cvm_duplicates['cnpj'].nunique():,}"
    )

    if not cvm_duplicates.empty:
        columns = [
            "cnpj",
            "Codigo_CVM",
            "Denominacao_Social",
            "Situacao",
            "Data_Registro",
        ]

        available_columns = [
            column
            for column in columns
            if column in cvm_duplicates.columns
        ]

        print()

        print(
            cvm_duplicates[
                available_columns
            ].to_string(
                index=False
            )
        )

    # -----------------------------------------
    # 2. CNPJs duplicados no Funds Explorer
    # -----------------------------------------

    funds_duplicates = funds[
        funds["cnpj"].duplicated(
            keep=False
        )
    ].copy()

    funds_duplicates = (
        funds_duplicates.sort_values(
            by=[
                "cnpj",
                "ticker",
            ]
        )
    )

    print(
        "\n======================================"
    )
    print(
        "CNPJs com múltiplos tickers"
    )
    print(
        "======================================"
    )

    print(
        f"Linhas envolvidas: "
        f"{len(funds_duplicates):,}"
    )

    print(
        f"CNPJs envolvidos: "
        f"{funds_duplicates['cnpj'].nunique():,}"
    )

    if not funds_duplicates.empty:
        print()

        print(
            funds_duplicates[
                [
                    "cnpj",
                    "ticker",
                    "fund_name",
                    "category_status",
                ]
            ].to_string(
                index=False
            )
        )

    # -----------------------------------------
    # 3. Quantidade de tickers por CNPJ
    # -----------------------------------------

    ticker_count = (
        funds.groupby(
            "cnpj"
        )["ticker"]
        .nunique()
        .sort_values(
            ascending=False
        )
    )

    multiple_tickers = (
        ticker_count[
            ticker_count > 1
        ]
    )

    print(
        "\n======================================"
    )
    print(
        "Distribuição ticker por CNPJ"
    )
    print(
        "======================================"
    )

    print(
        f"CNPJs com mais de um ticker: "
        f"{len(multiple_tickers):,}"
    )

    if not multiple_tickers.empty:
        print()

        print(
            multiple_tickers.to_string()
        )

    # -----------------------------------------
    # 4. Join somente para medir multiplicação
    # -----------------------------------------

    joined = cvm.merge(
        funds,
        how="inner",
        on="cnpj",
    )

    join_counts = (
        joined.groupby(
            "cnpj"
        )
        .size()
        .sort_values(
            ascending=False
        )
    )

    multiplied = (
        join_counts[
            join_counts > 1
        ]
    )

    print(
        "\n======================================"
    )
    print(
        "CNPJs produzindo múltiplas linhas no JOIN"
    )
    print(
        "======================================"
    )

    print(
        f"CNPJs: "
        f"{len(multiplied):,}"
    )

    if not multiplied.empty:
        print()

        print(
            multiplied.to_string()
        )

    print(
        "\nDiagnóstico concluído."
    )


if __name__ == "__main__":
    main()