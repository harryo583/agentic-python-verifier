---- MODULE RWLock_Abs ----
EXTENDS Naturals

CONSTANTS MaxReaders

VARIABLES state, reader_count

vars == << state, reader_count >>

TypeOK ==
  /\ state \in {"free","read","write"}
  /\ reader_count \in 0..MaxReaders

Init ==
  /\ state = "free"
  /\ reader_count = 0

AcquireRead ==
  /\ state \in {"free","read"}
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
  /\ reader_count' = reader_count

ReleaseWrite ==
  /\ state = "write"
  /\ state' = "free"
  /\ reader_count' = reader_count

Next == AcquireRead \/ ReleaseRead \/ AcquireWrite \/ ReleaseWrite

Spec == Init /\ [][Next]_vars

Inv ==
  /\ TypeOK
  /\ (state = "write") => (reader_count = 0)
  /\ (state = "read")  => (reader_count >= 1)
  /\ (state = "free")  => (reader_count = 0)
====
