package com.example;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class FibonacciTest {

    @Test
    public void testFibonacciFirstFiveTerms() {
        Fibonacci fibonacci = new Fibonacci();
        int[] expected = {0, 1, 1, 2, 3};
        assertArrayEquals(expected, fibonacci.generateFibonacci(5));
    }

    @Test
    public void testInvalidInput() {
        Fibonacci fibonacci = new Fibonacci();
        assertThrows(IllegalArgumentException.class, () -> fibonacci.generateFibonacci(-1));
    }
}
