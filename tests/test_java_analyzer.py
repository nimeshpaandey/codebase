from app.analyzers.java_analyzer import JavaAnalyzer
from app.schemas.finding import Category, Severity

def test_java_string_comparison():
    analyzer = JavaAnalyzer()
    code = """
public class Auth {
    public boolean checkRole(String role) {
        if (role == "admin") {
            return true;
        }
        return false;
    }
}
"""
    findings = analyzer.analyze(code, "Auth.java")
    assert any("String comparison using reference equality" in f.title for f in findings)

def test_java_array_bounds():
    analyzer = JavaAnalyzer()
    code = """
public class TestArray {
    public static void main(String[] args) {
        int[] data = new int[5];
        data[12] = 100;
    }
}
"""
    findings = analyzer.analyze(code, "TestArray.java")
    assert any("Array index out of bounds" in f.title for f in findings)

def test_java_null_dereference():
    analyzer = JavaAnalyzer()
    code = """
public class NullTest {
    public void test() {
        String msg = null;
        System.out.println(msg.toLowerCase());
    }
}
"""
    findings = analyzer.analyze(code, "NullTest.java")
    assert any("NullPointerException" in f.title for f in findings)

def test_java_clean_code():
    analyzer = JavaAnalyzer()
    code = """
import java.util.Objects;

public class CleanJava {
    public boolean check(String a, String b) {
        return Objects.equals(a, b);
    }
}
"""
    findings = analyzer.analyze(code, "CleanJava.java")
    assert len(findings) == 0
