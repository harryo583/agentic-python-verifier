---- MODULE WriteThroughCacheSystem ----
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Keys, Vals, Missing

VARIABLES store, cache

S == INSTANCE BackingStore_Impl WITH store <- store
C == INSTANCE FrontCache_Impl WITH cache <- cache

vars == <<store, cache>>

Init == S!Init /\ C!Init
Next == S!Next /\ C!Next
Spec == Init /\ [][Next]_vars

StoreOK ==
  \E D \in SUBSET Keys : store \in [D -> Vals]

CacheOK ==
  \E D \in SUBSET Keys : cache \in [D -> Vals]

Inv ==
  /\ StoreOK
  /\ CacheOK

Property == StoreOK /\ CacheOK

====
