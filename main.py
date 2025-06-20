import QuantumRingsLib
from QuantumRingsLib import (QuantumRegister as QRQuantumRegister,
                           AncillaRegister, ClassicalRegister as QRClassicalRegister,
                           QuantumCircuit as QRQuantumCircuit,
                           QuantumRingsProvider, job_monitor)
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
import numpy as np
from math import gcd, log2
from fractions import Fraction
import time
from concurrent.futures import ThreadPoolExecutor

# Configuration
QUANTUM_RINGS_TOKEN = 'TOKEN'
QUANTUM_RINGS_USER = 'USER'
SHOTS = 4096
MAX_QUBITS = 128
MAX_PARALLEL_JOBS = 8

class LargeNumberHandler:
    @staticmethod
    def modular_exponentiation(base: int, exponent: int, modulus: int) -> int:
        """Efficient modular exponentiation for large numbers"""
        result = 1
        base = base % modulus
        while exponent > 0:
            if exponent % 2 == 1:
                result = (result * base) % modulus
            base = (base * base) % modulus
            exponent //= 2
        return result

class OptimizedQuantumRings:
    def __init__(self):
        self.provider = QuantumRingsProvider(
            token=QUANTUM_RINGS_TOKEN, name=QUANTUM_RINGS_USER
        )
        self.backend = self.provider.get_backend("scarlet_quantum_rings")
    
    def execute_circuits(self, circuits):
        def execute_with_retry(circuit, max_retries=3):
            for attempt in range(max_retries):
                try:
                    job = self.backend.run(circuit, shots=SHOTS)
                    job_monitor(job)
                    return job.result().get_counts()
                except Exception:
                    time.sleep(2 ** attempt)
            return {}
        
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_JOBS) as executor:
            futures = [executor.submit(execute_with_retry, circuit) for circuit in circuits]
            return [future.result() for future in futures]

class LargeNumberShorCircuit:
    def __init__(self, N: int):
        self.N = N
        self.n = len(bin(N)) - 2
        self.total_qubits = min(MAX_QUBITS, 3 * self.n + 2)
    
    def create_quantum_circuits(self, a: int) -> QRQuantumCircuit:
        control = QRQuantumRegister(2 * self.n, 'control')
        target = QRQuantumRegister(self.n, 'target')
        ancilla = AncillaRegister(2, 'ancilla')
        classical = QRClassicalRegister(2 * self.n, 'classical')
        circuit = QRQuantumCircuit(control, target, ancilla, classical)
        self._build_circuit(circuit, control, target, ancilla, a)
        return circuit
    
    def _build_circuit(self, circuit, control, target, ancilla, a):
        for qubit in control:
            circuit.h(qubit)
        for i, ctrl in enumerate(control):
            power = 2 ** i
            result = LargeNumberHandler.modular_exponentiation(a, power, self.N)
            binary = bin(result)[2:].zfill(len(target))
            circuit.cx(ctrl, ancilla[0])
            for j, bit in enumerate(reversed(binary)):
                if bit == '1':
                    circuit.ccx(ancilla[0], ctrl, target[j])
            circuit.cx(ctrl, ancilla[0])
        circuit.measure(control, classical)

def optimized_period_finding(counts, N):
    """Enhanced period finding"""
    total_shots = sum(counts.values())
    threshold = 0.02 * total_shots
    phases = [int(output, 2) / (2 ** len(output)) for output, count in counts.items() if count >= threshold]
    candidates = [Fraction(phase).limit_denominator(N).denominator for phase in phases]
    return min((r for r in candidates if r % 2 == 0 and 1 < r < N), default=None)

def run_shors_algorithm(N):
    qr = OptimizedQuantumRings()
    circuit_generator = LargeNumberShorCircuit(N)
    start_time = time.time()
    while True:
        try:
            bases = [np.random.randint(2, min(N, 2**32)) for _ in range(MAX_PARALLEL_JOBS)]
            for a in bases:
                factor = gcd(a, N)
                if 1 < factor < N:
                    return factor, N // factor, time.time() - start_time
            circuits = [circuit_generator.create_quantum_circuits(a) for a in bases]
            results = qr.execute_circuits(circuits)
            for a, counts in zip(bases, results):
                if not counts:
                    continue
                period = optimized_period_finding(counts, N)
                if period and period % 2 == 0:
                    x = LargeNumberHandler.modular_exponentiation(a, period // 2, N)
                    for factor in (gcd(x-1, N), gcd(x+1, N)):
                        if 1 < factor < N:
                            return factor, N // factor, time.time() - start_time
        except Exception:
            pass

def main():
    while True:
        try:
            number_str = input("\nEnter a number to factor (0 to exit): ")
            if number_str == "0":
                break
            if not number_str.isdigit():
                print("Invalid input. Enter a positive integer.")
                continue
            N = int(number_str)
            if N < 4:
                print("Enter a number greater than 3")
                continue
            print("\nFactoring... This may take time.")
            while True:
                p, q, execution_time = run_shors_algorithm(N)
                if p and q:
                    print(f"\nFactors found: p = {p}, q = {q}, Verification: {p} × {q} = {N}")
                    break
                else:
                    print("Retrying...")
            print(f"Execution time: {execution_time:.2f} seconds")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()