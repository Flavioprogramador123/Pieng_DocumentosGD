from equipment_validation import equipment_list_error, validate_modules_inverters


def test_missing_module_quantity():
    err = validate_modules_inverters(
        [{'model': 'X', 'power': '620'}],
        [{'quantity': '2', 'power': '25'}],
    )
    assert err == 'Informe a quantidade de módulos.'


def test_missing_module_power():
    err = validate_modules_inverters(
        [{'quantity': '10'}],
        [{'quantity': '2', 'power': '25'}],
    )
    assert err == 'Informe a potência (Wp) dos módulos.'


def test_missing_inverter_quantity():
    err = validate_modules_inverters(
        [{'quantity': '10', 'power': '620'}],
        [{'model': 'SAJ', 'power': '25'}],
    )
    assert err == 'Informe a quantidade de inversores.'


def test_empty_module_list():
    err = equipment_list_error(
        [],
        empty_list_msg='Adicione pelo menos um módulo na aba Equipamentos.',
        label_plural='módulos',
        power_unit='Wp',
    )
    assert 'módulo' in err.lower()
