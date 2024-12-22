// Typescript Test Script
function add(a: number, b: number): number {
    return a + b;
}

class Greeter {
    greet(name: string): string {
        return `Hello, ${name}!`;
    }
}

console.log("Sum:", add(5, 3));
const greeter = new Greeter();
console.log(greeter.greet("World"));
