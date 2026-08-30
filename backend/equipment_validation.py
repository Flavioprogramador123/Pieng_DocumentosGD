"""Validação de listas de módulos/inversores antes dos cálculos."""

from __future__ import annotations

from typing import Any


def _first_value(item: dict, keys: tuple[str, ...]) -> Any:
    for key in keys:
        val = item.get(key)
        if val not in (None, ''):
            return val
    return None


def _parse_qty(value: Any) -> int | None:
    try:
        n = int(float(str(value).replace(',', '.').strip()))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _parse_power(value: Any) -> float | None:
    try:
        n = float(str(value).replace(',', '.').strip())
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def equipment_list_error(
    items: list,
    *,
    empty_list_msg: str,
    label_plural: str,
    power_unit: str,
    qty_keys: tuple[str, ...] = ('quantity', 'quantidade'),
    power_keys: tuple[str, ...] = ('power', 'potencia'),
) -> str | None:
    """Retorna mensagem específica ou None se houver pelo menos um item válido."""
    if not items:
        return empty_list_msg

    has_qty = False
    has_power = False
    for item in items:
        if not isinstance(item, dict):
            continue
        qty_raw = _first_value(item, qty_keys)
        pwr_raw = _first_value(item, power_keys)
        if qty_raw not in (None, ''):
            has_qty = True
        if pwr_raw not in (None, ''):
            has_power = True
        if _parse_qty(qty_raw) and _parse_power(pwr_raw):
            return None

    if not has_qty and not has_power:
        return f'Informe quantidade e potência ({power_unit}) dos {label_plural}.'
    if not has_qty:
        return f'Informe a quantidade de {label_plural}.'
    if not has_power:
        return f'Informe a potência ({power_unit}) dos {label_plural}.'
    return f'Quantidade e potência dos {label_plural} devem ser números maiores que zero.'


def validate_modules_inverters(modules: list, inverters: list) -> str | None:
    """Valida módulos e inversores; junta mensagens quando ambos falham."""
    errors: list[str] = []
    mod_err = equipment_list_error(
        modules,
        empty_list_msg='Adicione pelo menos um módulo na aba Equipamentos.',
        label_plural='módulos',
        power_unit='Wp',
    )
    if mod_err:
        errors.append(mod_err)
    inv_err = equipment_list_error(
        inverters,
        empty_list_msg='Adicione pelo menos um inversor na aba Equipamentos.',
        label_plural='inversores',
        power_unit='kW',
    )
    if inv_err:
        errors.append(inv_err)
    return ' '.join(errors) if errors else None
