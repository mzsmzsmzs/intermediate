package com.example;

public class Fibonacci {
    public void printFibonacci(int n) {
        int a = 0, b = 1, c;
        System.out.println("First " + n + " terms: ");
        for (int i = 1; i <= n; ++i) {
            System.out.println(a);  // Corrected to print `a`
            c = a + b;
            a = b;
            b = c;
        }
    }

    public int[] generateFibonacci(int n) {
        if (n <= 0) throw new IllegalArgumentException("n must be greater than 0");

        int[] series = new int[n];
        int a = 0, b = 1, c;
        for (int i = 0; i < n; ++i) {
            series[i] = a;
            c = a + b;
            a = b;
            b = c;
        }
        return series;
    }
}
