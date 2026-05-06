------------------------------ MODULE BoundedCounter ------------------------------
EXTENDS Integers

CONSTANTS MinValue, MaxValue

(* --algorithm BoundedCounter
variables counter = 0;
begin
  Increment:
    if counter < 10 then
      counter := counter + 1;
    end if;
end algorithm; *)

Invariant == counter >= 0 /\ counter <= 10
Property == Invariant

\* Proof obligations:
\* Initiation: Init => Invariant
\* Consecution: Invariant /\ Next => Invariant'
\* Property Implication: Invariant => Property

=============================================================================