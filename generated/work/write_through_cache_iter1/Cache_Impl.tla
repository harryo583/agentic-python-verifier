---- MODULE Cache_Impl ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Keys, Vals, Missing

(* --algorithm Cache
variables
  store = [k \in Keys |-> Missing],
  cache = [k \in Keys |-> Missing],
  lastReadValid = FALSE,
  lastReadKey = CHOOSE k \in Keys : TRUE,
  lastReadVal = Missing;
begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Vals do
          cache[k] := v ||
          store[k] := v;
          lastReadValid := FALSE;
          lastReadVal := Missing;
        end with;
      or
        with k \in Keys do
          if cache[k] # Missing then
            lastReadValid := TRUE ||
            lastReadKey := k ||
            lastReadVal := cache[k];
          else
            cache[k] := store[k];
            lastReadValid := TRUE ||
            lastReadKey := k ||
            lastReadVal := store[k];
          end if;
        end with;
      or
        with k \in Keys do
          cache[k] := Missing;
        end with;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "9687aa39" /\ chksum(tla) = "e5b2d675")
VARIABLES store, cache, lastReadValid, lastReadKey, lastReadVal

vars == << store, cache, lastReadValid, lastReadKey, lastReadVal >>

Init == (* Global variables *)
        /\ store = [k \in Keys |-> Missing]
        /\ cache = [k \in Keys |-> Missing]
        /\ lastReadValid = FALSE
        /\ lastReadKey = (CHOOSE k \in Keys : TRUE)
        /\ lastReadVal = Missing

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  /\ /\ cache' = [cache EXCEPT ![k] = v]
                     /\ store' = [store EXCEPT ![k] = v]
                  /\ lastReadValid' = FALSE
                  /\ lastReadVal' = Missing
           /\ UNCHANGED lastReadKey
        \/ /\ \E k \in Keys:
                IF cache[k] # Missing
                   THEN /\ /\ lastReadKey' = k
                           /\ lastReadVal' = cache[k]
                           /\ lastReadValid' = TRUE
                        /\ cache' = cache
                   ELSE /\ cache' = [cache EXCEPT ![k] = store[k]]
                        /\ /\ lastReadKey' = k
                           /\ lastReadVal' = store[k]
                           /\ lastReadValid' = TRUE
           /\ store' = store
        \/ /\ \E k \in Keys:
                cache' = [cache EXCEPT ![k] = Missing]
           /\ UNCHANGED <<store, lastReadValid, lastReadKey, lastReadVal>>

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

InvImpl ==
  /\ store \in [Keys -> (Vals \cup {Missing})]
  /\ cache \in [Keys -> (Vals \cup {Missing})]
  /\ lastReadValid \in BOOLEAN
  /\ lastReadKey \in Keys
  /\ lastReadVal \in (Vals \cup {Missing})
  /\ \A k \in Keys : (cache[k] # Missing) => (cache[k] = store[k])
  /\ lastReadValid => (lastReadVal = store[lastReadKey])

PropertyImpl == InvImpl
====
