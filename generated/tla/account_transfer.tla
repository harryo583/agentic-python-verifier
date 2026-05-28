---- MODULE AccountTransfer ----
EXTENDS Integers

CONSTANTS InitA, InitB, MaxAmount

Total == InitA + InitB

(* --algorithm AccountTransfer
variables
    a = InitA,
    b = InitB;

begin
  Loop:
    while TRUE do
      either
        with amt \in 1..MaxAmount do
          if a >= amt then
            a := a - amt;
            b := b + amt;
          end if;
        end with;
      or
        with amt \in 1..MaxAmount do
          if b >= amt then
            b := b - amt;
            a := a + amt;
          end if;
        end with;
      end either;
    end while;
end algorithm; *)
\* BEGIN TRANSLATION (chksum(pcal) = "21443aa5" /\ chksum(tla) = "6170ed9a")
VARIABLES a, b

vars == << a, b >>

Init == (* Global variables *)
        /\ a = InitA
        /\ b = InitB

Next == \/ /\ \E amt \in 1..MaxAmount:
                IF a >= amt
                   THEN /\ a' = a - amt
                        /\ b' = b + amt
                   ELSE /\ TRUE
                        /\ UNCHANGED << a, b >>
        \/ /\ \E amt \in 1..MaxAmount:
                IF b >= amt
                   THEN /\ b' = b - amt
                        /\ a' = a + amt
                   ELSE /\ TRUE
                        /\ UNCHANGED << a, b >>

Spec == Init /\ [][Next]_vars

\* END TRANSLATION 

Inv ==
    /\ a \in 0..Total
    /\ b \in 0..Total
    /\ a + b = Total

Property ==
    /\ a >= 0
    /\ b >= 0
    /\ a + b = Total

====
