# Python Test Script
def add(a, b):
    return a + b

class Greeter:
    def greet(self, name):
        return f"Hello, {name}!"

if __name__ == "__main__":
    print("Sum:", add(5, 3))
    greeter = Greeter()
    print(greeter.greet("World"))
