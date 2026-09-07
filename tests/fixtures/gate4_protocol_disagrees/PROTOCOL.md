SIMULATED DATA — NOT A SCIENTIFIC RESULT

# Fixture: a PROTOCOL.md that disagrees with itself about B

Section 7.3 says the patient-clustered bootstrap uses B = 2000 replicates.

Section 11 says Stage 2 recovery uses B = 5000 replicates.

This fixture exists only to prove gate4_statistics.py detects and rejects
this internal inconsistency rather than silently picking one value.
