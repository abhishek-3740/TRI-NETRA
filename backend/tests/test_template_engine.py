from app.parsers.template_engine import TemplateEngine


def test_save_and_retrieve_template(tmp_path):
    engine = TemplateEngine(template_dir=tmp_path)
    engine.save_template("test_bank", {"Date": "date", "Debit": "amount_debit"}, "%d/%m/%Y")
    template = engine.get_template("test_bank")
    assert template["column_map"]["Date"] == "date"


def test_detect_template_requires_min_overlap(tmp_path):
    engine = TemplateEngine(template_dir=tmp_path)
    engine.save_template("test_bank", {"Date": "date", "Debit": "amount_debit"}, "%d/%m/%Y")
    assert engine.detect_template(["Date", "Debit"]) is not None
    assert engine.detect_template(["Unrelated Column"]) is None
