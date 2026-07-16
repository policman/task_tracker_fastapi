from app.utils.csv_parser import parse_csv_generator


class TestCsvParser:

    def test_parse_csv_generator_happy_path(self, tmp_path):
        csv_file = tmp_path / "test.csv"

        csv_content = "id,name,role\n1,admin,superuser\n2,user,manager\n"
        csv_file.write_text(csv_content, encoding="utf-8")

        generator = parse_csv_generator(str(csv_file))

        result = list(generator)

        assert len(result) == 2

        assert result[0] == (2, {"id": "1", "name": "admin", "role": "superuser"})
        assert result[1] == (3, {"id": "2", "name": "user", "role": "manager"})

    def test_parse_csv_generator_skips_empty_rows(self, tmp_path):
        csv_file = tmp_path / "test_empty.csv"

        csv_content = "name,age\nВаня,20\n,\nПетя,30\n"
        csv_file.write_text(csv_content, encoding="utf-8")

        result = list(parse_csv_generator(str(csv_file)))

        assert len(result) == 2
        assert result[0] == (2, {"name": "Ваня", "age": "20"})
        assert result[1] == (4, {"name": "Петя", "age": "30"})

    def test_parse_csv_generator_custom_delimiter(self, tmp_path):
        csv_file = tmp_path / "test_semicolon.csv"
        csv_file.write_text("item;price\napple;100\n", encoding="utf-8")

        result = list(parse_csv_generator(str(csv_file)))

        assert len(result) == 1
        assert result[0] == (2, {"item": "apple", "price": "100"})
