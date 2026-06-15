# Makes `tests` an explicit package so `from tests.conftest import ...` resolves
# to this local package rather than any same-named package on sys.path.
