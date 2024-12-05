package com.example;

public class Fibonacci {
    public void printFibonacci(int n) {
        int a = 0, b = 1, c;
        System.out.println("First " + n + " terms: ");
        for (int i = 1; i <= n; ++i) {
            System.out.println(a+b);
            c = a + b;
            a = b;
            b = c;
        }
    }

}
