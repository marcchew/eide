// Javascript Test Script
function add(a, b) {
    return a + b;
}

class Greeter {
    greet(name) {
        return `Hello, ${name}!`;
    }
}

console.log("Sum:", add(5, 3));
const greeter = new Greeter();
console.log(greeter.greet("World"));