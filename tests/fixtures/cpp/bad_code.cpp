#include <iostream>

int main() {
    int arr[5];
    // Known Bug 1: Out of bounds (Memory Safety)
    arr[10] = 50; 
    
    // Known Bug 2: Uninitialized variable (Correctness)
    int uninit_val;
    std::cout << uninit_val << std::endl;

    return 0;
}