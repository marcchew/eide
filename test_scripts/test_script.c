// C Test Script
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

void greet(const char* name) {
    printf("Hello, %s!\n", name);
}

int main() {
    printf("Sum: %d\n", add(5, 3));
    greet("World");
    return 0;
}
