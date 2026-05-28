---- MODULE FrontCache_Abs ----
EXTENDS Naturals, FiniteSets

CONSTANTS Keys, Vals, Missing

VARIABLES cache

vars == <<cache>>

TypeOK ==
  \E D \in SUBSET Keys : cache \in [D -> Vals]

Init == cache = [k \in {} |-> 0]

CacheUpdate(k, v) ==
  /\ k \in Keys
  /\ v \in Vals
  /\ cache' = [x \in (DOMAIN cache) \cup {k} |-> IF x = k THEN v ELSE cache[x]]

CacheInvalidate(k) ==
  /\ k \in Keys
  /\ cache' = [x \in (DOMAIN cache) \ {k} |-> cache[x]]

CacheLookupStep ==
  UNCHANGED cache

Next ==
  \/ \E k \in Keys, v \in Vals : CacheUpdate(k, v)
  \/ \E k \in Keys : CacheInvalidate(k)
  \/ CacheLookupStep

Spec == Init /\ [][Next]_vars

Inv == TypeOK
Property == TypeOK

====
