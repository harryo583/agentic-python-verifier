---- MODULE WriteThroughCacheSystem ----
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Keys, Vals, Missing

VARIABLES store, cache, pcS, pcC

vars == << store, cache, pcS, pcC >>

PartialFn(Dom, Rng) == UNION { [S -> Rng] : S \in SUBSET Dom }

StoreOK == store \in PartialFn(Keys, Vals)
CacheOK == cache \in PartialFn(Keys, Vals)

CacheAgrees == \A k \in DOMAIN cache :
                  /\ k \in DOMAIN store
                  /\ cache[k] = store[k]

Inv == /\ StoreOK
       /\ CacheOK
       /\ CacheAgrees
       /\ pcS \in {"Loop", "Finish", "Done"}
       /\ pcC \in {"Loop", "Finish", "Done"}

Property == CacheAgrees

Init == /\ store = [k \in {} |-> 0]
        /\ cache = [k \in {} |-> 0]
        /\ pcS = "Loop"
        /\ pcC = "Loop"

\* Backing store may only write directly to uncached keys; cached keys must go through cache.
StoreStep ==
  /\ pcS = "Loop"
  /\ \E k \in Keys, v \in Vals :
       /\ k \notin DOMAIN cache
       /\ store' = [j \in (DOMAIN store) \cup {k} |-> IF j = k THEN v ELSE store[j]]
  /\ pcS' = "Loop"
  /\ UNCHANGED << cache, pcC >>

CacheWriteThrough ==
  /\ pcC = "Loop"
  /\ \E k \in Keys, v \in Vals :
       /\ cache' = [j \in (DOMAIN cache) \cup {k} |-> IF j = k THEN v ELSE cache[j]]
       /\ store' = [j \in (DOMAIN store) \cup {k} |-> IF j = k THEN v ELSE store[j]]
  /\ pcC' = "Loop"
  /\ UNCHANGED << pcS >>

CachePopulate ==
  /\ pcC = "Loop"
  /\ \E k \in Keys :
       /\ k \in DOMAIN store
       /\ k \notin DOMAIN cache
       /\ cache' = [j \in (DOMAIN cache) \cup {k} |-> IF j = k THEN store[j] ELSE cache[j]]
  /\ pcC' = "Loop"
  /\ UNCHANGED << store, pcS >>

Next == StoreStep \/ CacheWriteThrough \/ CachePopulate

Spec == Init /\ [][Next]_vars

====
