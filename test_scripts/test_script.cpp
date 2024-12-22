// C++ Test Script
#include <iostream>
#include <string>

int add(int a, int b) {
    return a + b;
}

class Greeter {
public:
    std::string greet(const std::string& name) {
        return "Hello, " + name + "!";
    }
};

int main() {
    std::cout << "Sum: " << add(5, 3) << std::endl;
    Greeter greeter;
    std::cout << greeter.greet("World") << std::endl;
    return 0;
}
