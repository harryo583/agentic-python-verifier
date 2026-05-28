---- MODULE Cache_Impl ----
EXTENDS Naturals, Sequences, TLC

CONSTANTS Keys, Vals

Zero == CHOOSE v \in Vals : \A w \in Vals : v <= w
SomeKey == CHOOSE k \in Keys : TRUE

(* --algorithm Cache
variables
  storePresent = [k \in Keys |-> FALSE],
  storeVal = [k \in Keys |-> Zero],
  cachePresent = [k \in Keys |-> FALSE],
  cacheVal = [k \in Keys |-> Zero],
  lastReadValid = FALSE,
  lastReadKey = SomeKey,
  lastReadVal = Zero;
begin
  Loop:
    while TRUE do
      either
        with k \in Keys, v \in Vals do
          cachePresent[k] := TRUE ||
          cacheVal[k] := v ||
          storePresent[k] := TRUE ||
          storeVal[k] := v;
          lastReadValid := FALSE;
        end with;
      or
        with k \in Keys do
          if cachePresent[k] then
            lastReadValid := TRUE ||
            lastReadKey := k ||
            lastReadVal := cacheVal[k];
          elsif storePresent[k] then
            cachePresent[k] := TRUE ||
            cacheVal[k] := storeVal[k];
            lastReadValid := TRUE ||
            lastReadKey := k ||
            lastReadVal := storeVal[k];
          else
            lastReadValid := FALSE ||
            lastReadKey := k;
          end if;
        end with;
      or
        with k \in Keys do
          cachePresent[k] := FALSE ||
          cacheVal[k] := Zero;
        end with;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "7a921abe" /\ chksum(tla) = "2e528aa4")
VARIABLES storePresent, storeVal, cachePresent, cacheVal, lastReadValid, 
          lastReadKey, lastReadVal

vars == << storePresent, storeVal, cachePresent, cacheVal, lastReadValid, 
           lastReadKey, lastReadVal >>

Init == (* Global variables *)
        /\ storePresent = [k \in Keys |-> FALSE]
        /\ storeVal = [k \in Keys |-> Zero]
        /\ cachePresent = [k \in Keys |-> FALSE]
        /\ cacheVal = [k \in Keys |-> Zero]
        /\ lastReadValid = FALSE
        /\ lastReadKey = SomeKey
        /\ lastReadVal = Zero

Next == \/ /\ \E k \in Keys:
                \E v \in Vals:
                  /\ /\ cachePresent' = [cachePresent EXCEPT ![k] = TRUE]
                     /\ cacheVal' = [cacheVal EXCEPT ![k] = v]
                     /\ storePresent' = [storePresent EXCEPT ![k] = TRUE]
                     /\ storeVal' = [storeVal EXCEPT ![k] = v]
                  /\ lastReadValid' = FALSE
           /\ UNCHANGED <<lastReadKey, lastReadVal>>
        \/ /\ \E k \in Keys:
                IF cachePresent[k]
                   THEN /\ /\ lastReadKey' = k
                           /\ lastReadVal' = cacheVal[k]
                           /\ lastReadValid' = TRUE
                        /\ UNCHANGED << cachePresent, cacheVal >>
                   ELSE /\ IF storePresent[k]
                              THEN /\ /\ cachePresent' = [cachePresent EXCEPT ![k] = TRUE]
                                      /\ cacheVal' = [cacheVal EXCEPT ![k] = storeVal[k]]
                                   /\ /\ lastReadKey' = k
                                      /\ lastReadVal' = storeVal[k]
                                      /\ lastReadValid' = TRUE
                              ELSE /\ /\ lastReadKey' = k
                                      /\ lastReadValid' = FALSE
                                   /\ UNCHANGED << cachePresent, cacheVal, 
                                                   lastReadVal >>
           /\ UNCHANGED <<storePresent, storeVal>>
        \/ /\ \E k \in Keys:
                /\ cachePresent' = [cachePresent EXCEPT ![k] = FALSE]
                /\ cacheVal' = [cacheVal EXCEPT ![k] = Zero]
           /\ UNCHANGED <<storePresent, storeVal, lastReadValid, lastReadKey, lastReadVal>>

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

InvImpl ==
  /\ storePresent \in [Keys -> BOOLEAN]
  /\ storeVal \in [Keys -> Vals]
  /\ cachePresent \in [Keys -> BOOLEAN]
  /\ cacheVal \in [Keys -> Vals]
  /\ lastReadValid \in BOOLEAN
  /\ lastReadKey \in Keys
  /\ lastReadVal \in Vals
  /\ \A k \in Keys : cachePresent[k] => /\ storePresent[k]
                                        /\ cacheVal[k] = storeVal[k]
  /\ lastReadValid => /\ storePresent[lastReadKey]
                      /\ lastReadVal = storeVal[lastReadKey]

PropertyImpl == InvImpl
====
