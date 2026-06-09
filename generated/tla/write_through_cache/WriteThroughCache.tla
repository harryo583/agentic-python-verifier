---- MODULE WriteThroughCache ----
EXTENDS Naturals, TLC, FiniteSets

CONSTANTS Keys, Vals, NoVal

VARIABLES store, cache, pcS, pcC

vars == << store, cache, pcS, pcC >>

EmptyFn == [x \in {} |-> 0]

IsPartialFn(f, Dom, Rng) == \E K \in SUBSET Dom : f \in [K -> Rng]

StoreWellFormed == IsPartialFn(store, Keys, Vals)
CacheWellFormed == IsPartialFn(cache, Keys, Vals)
Coherent == \A k \in DOMAIN cache : k \in DOMAIN store /\ cache[k] = store[k]

WriteThrough(k, v) ==
  /\ store' = [j \in (DOMAIN store) \cup {k} |-> IF j = k THEN v ELSE store[j]]
  /\ cache' = [j \in (DOMAIN cache) \cup {k} |-> IF j = k THEN v ELSE cache[j]]
  /\ UNCHANGED << pcS, pcC >>

ReadHit(k) ==
  /\ k \in DOMAIN cache
  /\ UNCHANGED << store, cache, pcS, pcC >>

ReadMiss(k) ==
  /\ k \notin DOMAIN cache
  /\ k \in DOMAIN store
  /\ cache' = [j \in (DOMAIN cache) \cup {k} |-> IF j = k THEN store[k] ELSE cache[j]]
  /\ UNCHANGED << store, pcS, pcC >>

ReadAbsent(k) ==
  /\ k \notin DOMAIN store
  /\ UNCHANGED << store, cache, pcS, pcC >>

Init == store = EmptyFn /\ cache = EmptyFn /\ pcS = "Loop" /\ pcC = "Loop"

Next == \E k \in Keys :
          \/ (\E v \in Vals : WriteThrough(k, v))
          \/ ReadHit(k)
          \/ ReadMiss(k)
          \/ ReadAbsent(k)

Spec == Init /\ [][Next]_vars

Inv == StoreWellFormed /\ CacheWellFormed /\ Coherent /\ pcS \in {"Loop"} /\ pcC \in {"Loop"}

Property == Coherent /\ StoreWellFormed /\ CacheWellFormed

====
