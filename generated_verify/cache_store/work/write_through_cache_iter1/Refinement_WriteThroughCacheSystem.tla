---- MODULE Refinement_WriteThroughCacheSystem ----
EXTENDS WriteThroughCacheSystem

Abs_BackingStore == INSTANCE BackingStore_Abs WITH
    Keys <- Keys,
    Vals <- Vals,
    Missing <- Missing,
    store <- store

Abs_FrontCache == INSTANCE FrontCache_Abs WITH
    Keys <- Keys,
    Vals <- Vals,
    Missing <- Missing,
    cache <- cache

RefinementSpec == /\ Abs_BackingStore!Spec
                  /\ Abs_FrontCache!Spec

====
