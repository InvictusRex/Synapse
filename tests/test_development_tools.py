"""
Tests for development tools: generate_template, list_templates, scaffold_project,
implement_section, generate_code
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock

from tools.all_tools import (
    generate_template,
    list_templates,
    scaffold_project,
    implement_section,
    generate_code,
    CODE_TEMPLATES,
    PROJECT_TEMPLATES,
    SECTION_TEMPLATES,
)


# ============================================================
# generate_template tests
# ============================================================

class TestGenerateTemplate:

    def test_python_class_template(self):
        result = generate_template("python:class", "UserService", "Manages users")
        assert result["success"] is True
        assert "class UserService" in result["code"]
        assert "Manages users" in result["code"]
        assert result["language"] == "python"
        assert result["template_type"] == "python:class"
        assert result["name"] == "UserService"

    def test_python_dataclass_template(self):
        result = generate_template("python:dataclass", "Config", "App config")
        assert result["success"] is True
        assert "@dataclass" in result["code"]
        assert "class Config" in result["code"]

    def test_python_function_template(self):
        result = generate_template("python:function", "process_data", "Process input data")
        assert result["success"] is True
        assert "def process_data" in result["code"]

    def test_python_test_template(self):
        result = generate_template("python:test", "Auth", "Authentication tests")
        assert result["success"] is True
        assert "class TestAuth" in result["code"]
        assert "unittest" in result["code"]

    def test_python_script_template(self):
        result = generate_template("python:script", "migrator", "Database migration script")
        assert result["success"] is True
        assert "argparse" in result["code"]
        assert "migrator" in result["code"]

    def test_python_flask_blueprint_template(self):
        result = generate_template("python:flask_blueprint", "users")
        assert result["success"] is True
        assert "Blueprint" in result["code"]
        assert "users_bp" in result["code"]

    def test_python_fastapi_router_template(self):
        result = generate_template("python:fastapi_router", "items")
        assert result["success"] is True
        assert "APIRouter" in result["code"]
        assert "items" in result["code"]

    def test_javascript_class_template(self):
        result = generate_template("javascript:class", "Logger")
        assert result["success"] is True
        assert "class Logger" in result["code"]
        assert result["language"] == "javascript"

    def test_javascript_function_template(self):
        result = generate_template("javascript:function", "validate")
        assert result["success"] is True
        assert "function validate" in result["code"]

    def test_javascript_express_router_template(self):
        result = generate_template("javascript:express_router", "products")
        assert result["success"] is True
        assert "express.Router" in result["code"]
        assert "products" in result["code"]

    def test_javascript_react_component_template(self):
        result = generate_template("javascript:react_component", "Dashboard")
        assert result["success"] is True
        assert "Dashboard" in result["code"]
        assert "export default" in result["code"]

    def test_javascript_test_template(self):
        result = generate_template("javascript:test", "UserService")
        assert result["success"] is True
        assert "describe" in result["code"]
        assert "UserService" in result["code"]

    def test_html_page_template(self):
        result = generate_template("html:page", "About")
        assert result["success"] is True
        assert "<!DOCTYPE html>" in result["code"]
        assert "About" in result["code"]

    def test_html_form_template(self):
        result = generate_template("html:form", "Contact")
        assert result["success"] is True
        assert "<form" in result["code"]
        assert "Contact" in result["code"]

    def test_unknown_template_type(self):
        result = generate_template("rust:struct", "MyStruct")
        assert result["success"] is False
        assert "available_templates" in result
        assert isinstance(result["available_templates"], list)

    def test_default_description(self):
        result = generate_template("python:function", "helper")
        assert result["success"] is True
        assert "helper implementation" in result["code"]

    def test_all_registered_templates_generate_successfully(self):
        for template_type in CODE_TEMPLATES:
            result = generate_template(template_type, "TestName", "Test description")
            assert result["success"] is True, f"Template {template_type} failed"
            assert result["code"], f"Template {template_type} produced empty code"


# ============================================================
# list_templates tests
# ============================================================

class TestListTemplates:

    def test_returns_success(self):
        result = list_templates()
        assert result["success"] is True

    def test_code_templates_structure(self):
        result = list_templates()
        code = result["code_templates"]
        assert "python" in code
        assert "javascript" in code
        assert "html" in code
        assert "class" in code["python"]
        assert "function" in code["python"]
        assert "react_component" in code["javascript"]

    def test_project_templates_present(self):
        result = list_templates()
        projects = result["project_templates"]
        assert "python" in projects
        assert "react" in projects
        assert "node" in projects
        assert "html" in projects
        assert "python-flask" in projects
        assert "python-fastapi" in projects
        assert "node-express" in projects

    def test_section_templates_present(self):
        result = list_templates()
        sections = result["section_templates"]
        assert "backend" in sections
        assert "frontend" in sections
        assert "database" in sections
        assert "api" in sections
        assert "testing" in sections

    def test_section_techs(self):
        result = list_templates()
        sections = result["section_templates"]
        assert "python" in sections["backend"]
        assert "node" in sections["backend"]
        assert "react" in sections["frontend"]
        assert "html" in sections["frontend"]
        assert "sql" in sections["database"]


# ============================================================
# scaffold_project tests
# ============================================================

class TestScaffoldProject:

    def test_scaffold_python_project(self, temp_dir):
        result = scaffold_project("MyApp", "python", temp_dir)
        assert result["success"] is True
        assert result["project_name"] == "MyApp"
        assert result["template"] == "python"
        assert os.path.isdir(os.path.join(temp_dir, "MyApp"))
        assert os.path.isfile(os.path.join(temp_dir, "MyApp", "main.py"))
        assert os.path.isfile(os.path.join(temp_dir, "MyApp", "requirements.txt"))
        assert os.path.isfile(os.path.join(temp_dir, "MyApp", ".gitignore"))
        assert os.path.isfile(os.path.join(temp_dir, "MyApp", "README.md"))

    def test_scaffold_react_project(self, temp_dir):
        result = scaffold_project("ReactApp", "react", temp_dir)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "ReactApp", "package.json"))
        assert os.path.isfile(os.path.join(temp_dir, "ReactApp", "src", "App.js"))
        assert os.path.isfile(os.path.join(temp_dir, "ReactApp", "src", "index.js"))
        assert os.path.isdir(os.path.join(temp_dir, "ReactApp", "src", "components"))

    def test_scaffold_node_express_project(self, temp_dir):
        result = scaffold_project("APIServer", "node-express", temp_dir)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "APIServer", "index.js"))
        pkg_path = os.path.join(temp_dir, "APIServer", "package.json")
        assert os.path.isfile(pkg_path)
        with open(pkg_path, 'r') as f:
            pkg = json.loads(f.read())
        assert "express" in pkg.get("dependencies", {})

    def test_scaffold_flask_project(self, temp_dir):
        result = scaffold_project("FlaskAPI", "python-flask", temp_dir)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "FlaskAPI", "app.py"))
        req_path = os.path.join(temp_dir, "FlaskAPI", "requirements.txt")
        with open(req_path, 'r') as f:
            assert "flask" in f.read().lower()

    def test_scaffold_fastapi_project(self, temp_dir):
        result = scaffold_project("FastApp", "python-fastapi", temp_dir)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "FastApp", "main.py"))
        assert os.path.isdir(os.path.join(temp_dir, "FastApp", "routers"))

    def test_scaffold_html_project(self, temp_dir):
        result = scaffold_project("Website", "html", temp_dir)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "Website", "index.html"))
        assert os.path.isdir(os.path.join(temp_dir, "Website", "css"))
        assert os.path.isdir(os.path.join(temp_dir, "Website", "js"))

    def test_scaffold_node_project(self, temp_dir):
        result = scaffold_project("NodeApp", "node", temp_dir)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "NodeApp", "index.js"))
        assert os.path.isfile(os.path.join(temp_dir, "NodeApp", "package.json"))

    def test_scaffold_unknown_template(self, temp_dir):
        result = scaffold_project("App", "golang", temp_dir)
        assert result["success"] is False
        assert "available_templates" in result

    def test_scaffold_existing_directory(self, temp_dir):
        os.makedirs(os.path.join(temp_dir, "Existing"))
        result = scaffold_project("Existing", "python", temp_dir)
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_scaffold_creates_folders(self, temp_dir):
        result = scaffold_project("App", "python", temp_dir)
        assert "tests" in result["folders_created"]
        assert "src" in result["folders_created"]
        assert os.path.isdir(os.path.join(temp_dir, "App", "tests"))
        assert os.path.isdir(os.path.join(temp_dir, "App", "src"))

    def test_scaffold_project_name_in_readme(self, temp_dir):
        result = scaffold_project("CoolProject", "python", temp_dir)
        readme_path = os.path.join(temp_dir, "CoolProject", "README.md")
        with open(readme_path, 'r') as f:
            content = f.read()
        assert "CoolProject" in content

    def test_scaffold_all_templates(self, temp_dir):
        """Verify every registered project template scaffolds successfully"""
        for template_name in PROJECT_TEMPLATES:
            project_name = f"Test_{template_name.replace('-', '_')}"
            result = scaffold_project(project_name, template_name, temp_dir)
            assert result["success"] is True, f"Template {template_name} failed: {result.get('error')}"
            assert len(result["files_created"]) > 0, f"Template {template_name} created no files"


# ============================================================
# implement_section tests
# ============================================================

class TestImplementSection:

    def test_implement_backend_python(self, temp_dir):
        result = implement_section("backend", "python", "TestProject", temp_dir)
        assert result["success"] is True
        assert result["section"] == "backend"
        assert result["tech"] == "python"
        backend_dir = os.path.join(temp_dir, "backend")
        assert os.path.isdir(backend_dir)
        assert os.path.isfile(os.path.join(backend_dir, "app.py"))
        assert os.path.isfile(os.path.join(backend_dir, "config.py"))
        assert os.path.isdir(os.path.join(backend_dir, "routes"))
        assert os.path.isdir(os.path.join(backend_dir, "models"))
        assert os.path.isdir(os.path.join(backend_dir, "services"))

    def test_implement_backend_node(self, temp_dir):
        result = implement_section("backend", "node", "TestProject", temp_dir)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "backend", "index.js"))
        assert os.path.isfile(os.path.join(temp_dir, "backend", "package.json"))
        assert os.path.isdir(os.path.join(temp_dir, "backend", "routes"))

    def test_implement_frontend_react(self, temp_dir):
        result = implement_section("frontend", "react", "TestProject", temp_dir)
        assert result["success"] is True
        frontend_dir = os.path.join(temp_dir, "frontend")
        assert os.path.isfile(os.path.join(frontend_dir, "src", "App.js"))
        assert os.path.isfile(os.path.join(frontend_dir, "src", "components", "Header.js"))
        assert os.path.isfile(os.path.join(frontend_dir, "src", "pages", "Home.js"))
        assert os.path.isfile(os.path.join(frontend_dir, "src", "styles", "global.css"))

    def test_implement_frontend_html(self, temp_dir):
        result = implement_section("frontend", "html", "TestProject", temp_dir)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "frontend", "index.html"))
        assert os.path.isfile(os.path.join(temp_dir, "frontend", "css", "style.css"))
        assert os.path.isfile(os.path.join(temp_dir, "frontend", "js", "main.js"))

    def test_implement_database_sql(self, temp_dir):
        result = implement_section("database", "sql", "TestProject", temp_dir)
        assert result["success"] is True
        db_dir = os.path.join(temp_dir, "database")
        assert os.path.isfile(os.path.join(db_dir, "schema.sql"))
        assert os.path.isfile(os.path.join(db_dir, "seed.sql"))
        assert os.path.isdir(os.path.join(db_dir, "migrations"))

    def test_implement_api_rest(self, temp_dir):
        result = implement_section("api", "rest", "TestProject", temp_dir)
        assert result["success"] is True
        api_dir = os.path.join(temp_dir, "api")
        assert os.path.isdir(os.path.join(api_dir, "routes"))
        assert os.path.isdir(os.path.join(api_dir, "middleware"))

    def test_implement_testing_python(self, temp_dir):
        result = implement_section("testing", "python", "TestProject", temp_dir)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "testing", "tests", "test_example.py"))
        assert os.path.isfile(os.path.join(temp_dir, "testing", "tests", "conftest.py"))

    def test_implement_testing_javascript(self, temp_dir):
        result = implement_section("testing", "javascript", "TestProject", temp_dir)
        assert result["success"] is True
        assert os.path.isfile(os.path.join(temp_dir, "testing", "tests", "example.test.js"))
        assert os.path.isfile(os.path.join(temp_dir, "testing", "jest.config.js"))

    def test_implement_unknown_section(self, temp_dir):
        result = implement_section("mobile", "swift", "TestProject", temp_dir)
        assert result["success"] is False
        assert "available_sections" in result

    def test_implement_unknown_tech(self, temp_dir):
        result = implement_section("backend", "rust", "TestProject", temp_dir)
        assert result["success"] is False
        assert "available_techs" in result

    def test_implement_has_description(self, temp_dir):
        result = implement_section("backend", "python", "TestProject", temp_dir)
        assert result["description"] != ""

    def test_implement_project_name_substitution(self, temp_dir):
        result = implement_section("frontend", "react", "SuperApp", temp_dir)
        assert result["success"] is True
        header_path = os.path.join(temp_dir, "frontend", "src", "components", "Header.js")
        with open(header_path, 'r') as f:
            content = f.read()
        assert "SuperApp" in content

    def test_implement_all_sections(self, temp_dir):
        """Verify every registered section/tech combo works"""
        for section, techs in SECTION_TEMPLATES.items():
            for tech in techs:
                sub_dir = os.path.join(temp_dir, f"{section}_{tech}")
                os.makedirs(sub_dir, exist_ok=True)
                result = implement_section(section, tech, "TestProject", sub_dir)
                assert result["success"] is True, f"{section}/{tech} failed: {result.get('error')}"
                assert len(result["files_created"]) > 0


# ============================================================
# generate_code tests
# ============================================================

class TestGenerateCode:

    def test_generate_code_success(self, mock_groq):
        mock_groq._response.choices[0].message.content = "def hello():\n    print('hello')"
        result = generate_code("a hello world function", "python")
        assert result["success"] is True
        assert result["language"] == "python"
        assert result["code"] == "def hello():\n    print('hello')"

    def test_generate_code_default_language(self, mock_groq):
        mock_groq._response.choices[0].message.content = "print('hi')"
        result = generate_code("print hi")
        assert result["success"] is True
        assert result["language"] == "python"

    def test_generate_code_javascript(self, mock_groq):
        mock_groq._response.choices[0].message.content = "console.log('hi');"
        result = generate_code("print hi", "javascript")
        assert result["success"] is True
        assert result["language"] == "javascript"

    def test_generate_code_no_api_key(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
            result = generate_code("test prompt")
            assert result["success"] is False
            assert "GROQ_API_KEY" in result["error"]

    def test_generate_code_api_error(self, mock_groq):
        mock_groq.return_value.chat.completions.create.side_effect = Exception("API limit reached")
        result = generate_code("test prompt")
        assert result["success"] is False
        assert "API limit reached" in result["error"]

    def test_generate_code_preserves_prompt(self, mock_groq):
        mock_groq._response.choices[0].message.content = "code"
        result = generate_code("build a REST API", "python")
        assert result["prompt"] == "build a REST API"
