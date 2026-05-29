---- MODULE WriteThroughCache ----
EXTENDS Integers, FiniteSets, Sequences, TLC

CONSTANTS Keys, Values, Missing

VARIABLES store, cache, pcS, pcC

vars == << store, cache, pcS, pcC >>

S == INSTANCE Store_Impl WITH store <- store, pc <- pcS
C == INSTANCE Cache_Impl WITH cache <- cache, pc <- pcC

Init == S!Init /\ C!Init

Next == (S!Next /\ UNCHANGED << cache, pcC >>)
     \/ (C!Next /\ UNCHANGED << store, pcS >>)

Spec == Init /\ [][Next]_vars

TypeOK ==
  /\ store \in [Keys -> Values \cup {Missing}]
  /\ cache \in [Keys -> Values \cup {Missing}]

CacheAgreesWithStore ==
  \A k \in Keys : cache[k] # Missing => cache[k] = store[k]

Inv ==
  /\ TypeOK
  /\ CacheAgreesWithStore
  /\ pcS \in {"Loop", "Finish", "Done"}
  /\ pcC \in {"Loop", "Finish", "Done"}

Read(k) == IF cache[k] # Missing THEN cache[k] ELSE store[k]

Property ==
  /\ \A k \in Keys : Read(k) \in Values \cup {Missing}
  /\ \A k \in Keys : (cache[k] # Missing) => (Read(k) = store[k])

====
