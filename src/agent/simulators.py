from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .simulator import _taxa_mensal, simular_price


def _money(value: float) -> float:
    return round(float(value), 2)


def _months(periodo: int, periodo_unidade: str) -> int:
    if periodo < 1:
        raise ValueError("periodo deve ser maior que zero")
    if periodo_unidade == "anos":
        return int(periodo) * 12
    if periodo_unidade == "meses":
        return int(periodo)
    raise ValueError("periodo_unidade invalida")


def _monthly_rate(taxa: float, taxa_periodo: str) -> float:
    if taxa < 0:
        raise ValueError("taxa nao pode ser negativa")
    if taxa_periodo == "anual":
        return _taxa_mensal(taxa)
    if taxa_periodo == "mensal":
        return taxa / 100
    raise ValueError("taxa_periodo invalido")


def _income_tax_rate(days: int) -> float:
    if days <= 180:
        return 22.5
    if days <= 360:
        return 20.0
    if days <= 720:
        return 17.5
    return 15.0


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(value, "%Y-%m-%d").date()


def _business_days(start: date, end: date) -> int:
    if end <= start:
        return 0
    total = 0
    cursor = start
    while cursor < end:
        if cursor.weekday() < 5:
            total += 1
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return total


def juros_compostos(
    *,
    valor_inicial: float,
    valor_mensal: float,
    taxa: float,
    taxa_periodo: str,
    periodo: int,
    periodo_unidade: str,
) -> dict[str, Any]:
    if valor_inicial < 0:
        raise ValueError("valor_inicial nao pode ser negativo")
    if valor_mensal < 0:
        raise ValueError("valor_mensal nao pode ser negativo")

    months = _months(periodo, periodo_unidade)
    monthly_rate = _monthly_rate(taxa, taxa_periodo)
    saldo = float(valor_inicial)
    investido = float(valor_inicial)
    total_juros = 0.0
    serie: list[dict[str, float | int]] = []

    for month in range(1, months + 1):
        juros = saldo * monthly_rate
        saldo += juros
        total_juros += juros
        serie.append(
            {
                "mes": month,
                "juros": _money(juros),
                "total_investido": _money(investido),
                "total_juros": _money(total_juros),
                "total_acumulado": _money(saldo),
            }
        )
        investido += float(valor_mensal)
        saldo += float(valor_mensal)

    return {
        "resumo": {
            "valor_final": _money(saldo),
            "total_investido": _money(investido),
            "total_juros": _money(saldo - investido),
        },
        "serie": serie,
    }


def renda_retiradas(
    *,
    valor_inicial: float,
    retirada_mensal: float,
    taxa: float,
    taxa_periodo: str,
    periodo: int,
    periodo_unidade: str,
) -> dict[str, Any]:
    if valor_inicial <= 0:
        raise ValueError("valor_inicial deve ser maior que zero")
    if retirada_mensal < 0:
        raise ValueError("retirada_mensal nao pode ser negativa")

    months = _months(periodo, periodo_unidade)
    monthly_rate = _monthly_rate(taxa, taxa_periodo)
    saldo = float(valor_inicial)
    total_juros = 0.0
    total_retirado = 0.0
    meses_ate_zerar: int | None = None
    serie: list[dict[str, float | int]] = []

    first_interest = saldo * monthly_rate
    for month in range(1, months + 1):
        juros = saldo * monthly_rate
        saldo += juros
        total_juros += juros
        saldo -= float(retirada_mensal)
        total_retirado += float(retirada_mensal)
        serie.append(
            {
                "mes": month,
                "juros": _money(juros),
                "valor_com_retiradas": _money(max(saldo, 0.0)),
                "total_juros": _money(total_juros),
                "retiradas": _money(total_retirado),
            }
        )
        if saldo <= 0:
            meses_ate_zerar = month
            saldo = 0.0
            break

    return {
        "resumo": {
            "valor_final": _money(saldo),
            "total_retirado": _money(total_retirado),
            "total_juros": _money(total_juros),
            "sustentavel": first_interest >= retirada_mensal,
            "meses_ate_zerar": meses_ate_zerar,
        },
        "serie": serie,
    }


def pix_parcelado(
    *,
    valor_pix: float,
    n_parcelas: int,
    juros_mensal_pct: float,
    incluir_valor_parcela: bool = False,
    valor_parcela: float | None = None,
) -> dict[str, Any]:
    if valor_pix <= 0:
        raise ValueError("valor_pix deve ser maior que zero")
    if n_parcelas < 1:
        raise ValueError("n_parcelas deve ser maior que zero")

    if incluir_valor_parcela:
        if valor_parcela is None or valor_parcela <= 0:
            raise ValueError("valor_parcela deve ser maior que zero")
        if valor_parcela * n_parcelas < valor_pix:
            raise ValueError("valor_parcela nao quita o valor_pix")
        if abs(valor_parcela * n_parcelas - valor_pix) < 0.000001:
            monthly_rate = 0.0
        else:
            low = 0.0
            high = 1.0
            for _ in range(100):
                mid = (low + high) / 2
                principal = valor_parcela * (1 - (1 + mid) ** (-n_parcelas)) / mid
                if principal > valor_pix:
                    low = mid
                else:
                    high = mid
            monthly_rate = (low + high) / 2
        parcela = float(valor_parcela)
    else:
        if juros_mensal_pct < 0:
            raise ValueError("juros_mensal_pct nao pode ser negativo")
        monthly_rate = juros_mensal_pct / 100
        if monthly_rate == 0:
            parcela = valor_pix / n_parcelas
        else:
            parcela = valor_pix * monthly_rate / (1 - (1 + monthly_rate) ** (-n_parcelas))

    total_pago = parcela * n_parcelas
    total_juros = total_pago - valor_pix
    cet_anual = ((1 + monthly_rate) ** 12 - 1) * 100
    return {
        "resumo": {
            "valor_parcela": _money(parcela),
            "total_pago": _money(total_pago),
            "total_juros": _money(total_juros),
            "cet_mensal_pct": _money(monthly_rate * 100),
            "cet_anual_pct": _money(cet_anual),
            "acrescimo_pct": _money((total_juros / valor_pix) * 100),
        }
    }


def cdb(
    *,
    investimento_inicial: float,
    investimento_mensal: float,
    cdi_pct: float,
    tempo: int,
    tempo_unidade: str,
    cdi_aa: float,
) -> dict[str, Any]:
    if cdi_pct < 0:
        raise ValueError("cdi_pct nao pode ser negativo")
    taxa_bruta_aa = float(cdi_aa) * float(cdi_pct) / 100
    months = _months(tempo, tempo_unidade)
    days = round(months * 365 / 12)
    aliquota = _income_tax_rate(days)
    bruto = juros_compostos(
        valor_inicial=investimento_inicial,
        valor_mensal=investimento_mensal,
        taxa=taxa_bruta_aa,
        taxa_periodo="anual",
        periodo=months,
        periodo_unidade="meses",
    )
    valor_bruto = bruto["resumo"]["valor_final"]
    total_investido = bruto["resumo"]["total_investido"]
    juros_bruto = _money(valor_bruto - total_investido)
    ir = _money(juros_bruto * aliquota / 100)
    valor_liquido = _money(valor_bruto - ir)
    return {
        "resumo": {
            "valor_bruto": valor_bruto,
            "valor_liquido": valor_liquido,
            "total_investido": total_investido,
            "juros_bruto": juros_bruto,
            "ir": ir,
            "aliquota_ir_pct": aliquota,
            "rendimento_liquido": _money(valor_liquido - total_investido),
        },
        "serie": bruto["serie"],
    }


def marcacao_mercado(
    *,
    tipo: str,
    data_aplicacao: str | date,
    data_vencimento: str | date,
    valor_investido: float,
    valor_atual_bruto: float,
    rentabilidade_contratada_aa: float,
    isento_ir: bool,
    ipca_projetado_aa: float | None = None,
    rentabilidade_nova_oferta_aa: float | None = None,
    nova_oferta_isenta_ir: bool = False,
    data_hoje: str | date | None = None,
) -> dict[str, Any]:
    start = _parse_date(data_aplicacao)
    maturity = _parse_date(data_vencimento)
    today = _parse_date(data_hoje) if data_hoje is not None else date.today()
    if maturity <= start:
        raise ValueError("data_vencimento deve ser maior que data_aplicacao")
    if today <= start:
        today = start
    if today >= maturity:
        raise ValueError("titulo vencido")
    if valor_investido <= 0 or valor_atual_bruto <= 0:
        raise ValueError("valores devem ser maiores que zero")

    kind = tipo.lower()
    contracted = rentabilidade_contratada_aa / 100
    if kind == "prefixado":
        nominal_rate = contracted
    elif kind == "ipca":
        projected_ipca = (ipca_projetado_aa or 0.0) / 100
        nominal_rate = (1 + contracted) * (1 + projected_ipca) - 1
    else:
        raise ValueError("tipo invalido")

    elapsed_bd = _business_days(start, today)
    remaining_bd = _business_days(today, maturity)
    total_bd = elapsed_bd + remaining_bd
    years_elapsed = elapsed_bd / 252
    years_remaining = remaining_bd / 252
    years_total = total_bd / 252
    if years_remaining <= 0:
        raise ValueError("titulo vencido")

    valor_na_curva = valor_investido * (1 + nominal_rate) ** years_elapsed
    valor_vencimento = valor_investido * (1 + nominal_rate) ** years_total
    aliquota_total = 0.0 if isento_ir else _income_tax_rate(round(years_total * 365))
    ir_manter = 0.0 if isento_ir else max(0.0, valor_vencimento - valor_investido) * aliquota_total / 100
    liq_manter = valor_vencimento - ir_manter
    aliquota_atual = 0.0 if isento_ir else _income_tax_rate(round(years_elapsed * 365))
    ir_venda = 0.0 if isento_ir else max(0.0, valor_atual_bruto - valor_investido) * aliquota_atual / 100
    caixa_hoje = valor_atual_bruto - ir_venda
    aliquota_novo = 0.0 if nova_oferta_isenta_ir else _income_tax_rate(round(years_remaining * 365))

    def net_reinvested(rate: float) -> float:
        gross = caixa_hoje * (1 + rate) ** years_remaining
        tax = 0.0 if nova_oferta_isenta_ir else max(0.0, gross - caixa_hoje) * aliquota_novo / 100
        return gross - tax

    low = -0.99
    high = 1.0
    while net_reinvested(high) < liq_manter and high < 10:
        high *= 2
    for _ in range(100):
        mid = (low + high) / 2
        if net_reinvested(mid) < liq_manter:
            low = mid
        else:
            high = mid
    target_rate = (low + high) / 2

    comparativo = None
    if rentabilidade_nova_oferta_aa is not None:
        offer_net = net_reinvested(rentabilidade_nova_oferta_aa / 100)
        comparativo = {
            "liq_oferta": _money(offer_net),
            "diferenca_rs": _money(offer_net - liq_manter),
            "vale_a_pena": offer_net > liq_manter,
        }

    return {
        "resumo": {
            "tipo": kind,
            "dias_corridos": (today - start).days,
            "dias_uteis": elapsed_bd,
            "anos_decorridos": round(years_elapsed, 4),
            "anos_restantes": round(years_remaining, 4),
            "valor_investido": _money(valor_investido),
            "valor_atual_bruto": _money(valor_atual_bruto),
            "valor_na_curva": _money(valor_na_curva),
            "agio_desagio": _money(valor_atual_bruto - valor_na_curva),
            "valor_vencimento": _money(valor_vencimento),
            "ir_manter": _money(ir_manter),
            "liq_manter": _money(liq_manter),
            "ir_venda": _money(ir_venda),
            "caixa_hoje": _money(caixa_hoje),
            "aliquota_ir_atual_pct": aliquota_atual,
            "tir_implicita_aa": _money(target_rate * 100),
            "comparativo_oferta": comparativo,
        }
    }


def _loan_schedule(
    *,
    valor_emprestimo: float,
    sistema: str,
    taxa: float,
    taxa_periodo: str,
    n_parcelas: int,
    correcao: str = "nenhuma",
    indice_correcao_aa: float | None = None,
    aportes_extra: list[dict[str, float | int]] | None = None,
    modo_aporte: str = "reduzir_prazo",
    seguros_taxas_mensal: float = 0.0,
) -> list[dict[str, float | int]]:
    if valor_emprestimo <= 0:
        raise ValueError("valor_emprestimo deve ser maior que zero")
    if n_parcelas < 1:
        raise ValueError("n_parcelas deve ser maior que zero")
    system = sistema.lower()
    if system not in {"price", "sac"}:
        raise ValueError("sistema invalido")
    if correcao not in {"nenhuma", "tr", "ipca"}:
        raise ValueError("correcao invalida")
    monthly_rate = _monthly_rate(taxa, taxa_periodo)
    correction_rate = _taxa_mensal(indice_correcao_aa or 0.0) if correcao != "nenhuma" else 0.0
    extra_by_month = {
        int(item["mes"]): float(item["valor"])
        for item in (aportes_extra or [])
        if int(item.get("mes", 0)) > 0 and float(item.get("valor", 0.0)) > 0
    }
    saldo = float(valor_emprestimo)
    remaining = int(n_parcelas)
    fixed_price = simular_price(valor_emprestimo, n_parcelas, taxa if taxa_periodo == "anual" else ((1 + monthly_rate) ** 12 - 1) * 100)["parcela"]
    sac_amortization = valor_emprestimo / n_parcelas
    serie: list[dict[str, float | int]] = []

    for month in range(1, n_parcelas + 1):
        if saldo <= 0:
            break
        if correction_rate:
            saldo *= 1 + correction_rate
        juros = saldo * monthly_rate
        if system == "price":
            parcela_base = fixed_price
            amortizacao = parcela_base - juros
            if amortizacao <= 0:
                raise ValueError("parcela nao cobre juros")
        else:
            amortizacao = min(sac_amortization, saldo)
            parcela_base = amortizacao + juros
        amortizacao = min(amortizacao, saldo)
        saldo -= amortizacao
        aporte = min(extra_by_month.get(month, 0.0), saldo)
        saldo -= aporte
        if saldo < 0.005:
            saldo = 0.0
        parcela_total = parcela_base + seguros_taxas_mensal
        serie.append(
            {
                "mes": month,
                "parcela": _money(parcela_total),
                "juros": _money(juros),
                "amortizacao": _money(amortizacao),
                "aporte_extra": _money(aporte),
                "saldo": _money(saldo),
                "seguro": _money(seguros_taxas_mensal),
            }
        )
        remaining -= 1
        if system == "price" and modo_aporte == "reduzir_parcela" and saldo > 0 and remaining > 0:
            if monthly_rate == 0:
                fixed_price = saldo / remaining
            else:
                fixed_price = saldo * monthly_rate / (1 - (1 + monthly_rate) ** (-remaining))
    return serie


def amortizacao_completa(
    *,
    valor_emprestimo: float,
    data_inicio: str | date,
    sistema: str,
    taxa: float,
    taxa_periodo: str,
    n_parcelas: int,
    correcao: str,
    indice_correcao_aa: float | None = None,
    aportes_extra: list[dict[str, float | int]] | None = None,
    modo_aporte: str = "reduzir_prazo",
    seguros_taxas_mensal: float = 0.0,
    modalidade: str | None = None,
) -> dict[str, Any]:
    _parse_date(data_inicio)
    baseline = _loan_schedule(
        valor_emprestimo=valor_emprestimo,
        sistema=sistema,
        taxa=taxa,
        taxa_periodo=taxa_periodo,
        n_parcelas=n_parcelas,
        correcao=correcao,
        indice_correcao_aa=indice_correcao_aa,
        seguros_taxas_mensal=seguros_taxas_mensal,
    )
    serie = _loan_schedule(
        valor_emprestimo=valor_emprestimo,
        sistema=sistema,
        taxa=taxa,
        taxa_periodo=taxa_periodo,
        n_parcelas=n_parcelas,
        correcao=correcao,
        indice_correcao_aa=indice_correcao_aa,
        aportes_extra=aportes_extra,
        modo_aporte=modo_aporte,
        seguros_taxas_mensal=seguros_taxas_mensal,
    )
    total_juros = _money(sum(float(row["juros"]) for row in serie))
    total_seguros = _money(sum(float(row["seguro"]) for row in serie))
    total_pago = _money(sum(float(row["parcela"]) + float(row["aporte_extra"]) for row in serie))
    baseline_interest = _money(sum(float(row["juros"]) for row in baseline))
    resumo: dict[str, Any] = {
        "parcela_inicial": serie[0]["parcela"],
        "parcela_final": serie[-1]["parcela"],
        "total_pago": total_pago,
        "total_juros": total_juros,
        "total_seguros": total_seguros,
        "meses": len(serie),
    }
    if aportes_extra:
        resumo["com_aporte"] = {
            "meses": len(serie),
            "total_juros": total_juros,
            "meses_economizados": len(baseline) - len(serie),
            "juros_economizados": _money(baseline_interest - total_juros),
        }
    return {"resumo": resumo, "serie": serie}


def aluguel_vs_financiamento(
    *,
    valor_imovel: float,
    entrada: float,
    custos_financiamento: float,
    prazo_meses: int,
    taxa_aa: float,
    sistema: str,
    aluguel_mensal: float,
    reajuste_aluguel_aa: float,
    rendimento_investimento_aa: float,
    valorizacao_imovel_aa: float,
) -> dict[str, Any]:
    if valor_imovel <= 0 or prazo_meses < 1:
        raise ValueError("entrada invalida")
    loan = max(0.0, valor_imovel - entrada)
    schedule = _loan_schedule(
        valor_emprestimo=loan,
        sistema=sistema,
        taxa=taxa_aa,
        taxa_periodo="anual",
        n_parcelas=prazo_meses,
        correcao="nenhuma",
    )
    investment = entrada + custos_financiamento
    invest_rate = _taxa_mensal(rendimento_investimento_aa)
    rent_rate = _taxa_mensal(reajuste_aluguel_aa)
    property_rate = _taxa_mensal(valorizacao_imovel_aa)
    rent = aluguel_mensal
    breakeven: int | None = None
    serie: list[dict[str, float | int]] = []

    for month in range(1, prazo_meses + 1):
        row = schedule[min(month - 1, len(schedule) - 1)]
        parcela = float(row["parcela"])
        saldo_devedor = float(row["saldo"])
        property_value = valor_imovel * (1 + property_rate) ** month
        patrimonio_comprar = property_value - saldo_devedor
        investment *= 1 + invest_rate
        if parcela > rent:
            investment += parcela - rent
        patrimonio_alugar = investment
        if breakeven is None and patrimonio_comprar >= patrimonio_alugar:
            breakeven = month
        serie.append(
            {
                "mes": month,
                "patrimonio_comprar": _money(patrimonio_comprar),
                "patrimonio_alugar": _money(patrimonio_alugar),
                "saldo_devedor": _money(saldo_devedor),
                "aluguel": _money(rent),
                "parcela": _money(parcela),
            }
        )
        rent *= 1 + rent_rate

    comprar = float(serie[-1]["patrimonio_comprar"])
    alugar = float(serie[-1]["patrimonio_alugar"])
    return {
        "resumo": {
            "patrimonio_final_comprar": _money(comprar),
            "patrimonio_final_alugar": _money(alugar),
            "vantagem": "comprar" if comprar >= alugar else "alugar",
            "breakeven_mes": breakeven,
        },
        "serie": serie,
    }
