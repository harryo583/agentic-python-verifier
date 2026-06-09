---- MODULE RWLock_Abs ----
EXTENDS Naturals

CONSTANTS MaxReaders

VARIABLES state, reader_count

vars == << state, reader_count >>

Init ==
  /\ state = "free"
  /\ reader_count = 0

AcquireRead ==
  /\ state \in {"free", "read"}
  /\ reader_count < MaxReaders
  /\ state' = "read"
  /\ reader_count' = reader_count + 1

ReleaseRead ==
  /\ state = "read"
  /\ reader_count > 0
  /\ reader_count' = reader_count - 1
  /\ state' = IF reader_count - 1 = 0 THEN "free" ELSE "read"

AcquireWrite ==
  /\ state = "free"
  /\ reader_count = 0
  /\ state' = "write"
  /\ UNCHANGED reader_count

ReleaseWrite ==
  /\ state = "write"
  /\ state' = "free"
  /\ UNCHANGED reader_count

Next == AcquireRead \/ ReleaseRead \/ AcquireWrite \/ ReleaseWrite

Spec == Init /\ [][Next]_vars

Inv ==
  /\ state \in {"free", "read", "write"}
  /\ reader_count \in 0..MaxReaders
  /\ (state = "write") => (reader_count = 0)
  /\ (state = "free") => (reader_count = 0)
  /\ (state = "read") => (reader_count >= 1)

Property == Inv
====
