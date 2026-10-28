import java.io.IOException;

public class BadCode {
    public static void main(String[] args) {
        // Known Bug 1: Array out of bounds (Memory Safety)
        int[] numbers = new int[5];
        numbers[10] = 99;

        // Known Bug 2: String reference equality comparison (Correctness)
        String userRole = "guest";
        if (userRole == "admin") {
            System.out.println("Granted");
        }

        // Known Bug 3: Insecure OS command execution (Security)
        try {
            Runtime.getRuntime().exec("ls -la");
        } catch (IOException e) {
            // Ignored
        }
    }
}
