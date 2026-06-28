import Lean
open Lean Meta Elab Command

/--
Recolecta recursivamente todas las constantes (Name) referenciadas en una expresión Lean.
-/
partial def collectConsts : Expr → List Name
  | .const name _ => [name]
  | .app fn arg => collectConsts fn ++ collectConsts arg
  | .lam _ _ body _ => collectConsts body
  | .forallE _ _ body _ => collectConsts body
  | .letE _ _ val body _ => collectConsts val ++ collectConsts body
  | .mdata _ e => collectConsts e
  | .proj _ _ e => collectConsts e
  | _ => []

/--
Dado un nombre de teorema, devuelve la lista de premisas (constantes referenciadas).
-/
def getPremises (constName : Name) : MetaM (List Name) := do
  let decl ← getConstInfo constName
  let mut premises := collectConsts decl.type
  match decl.value? with
  | some proof => premises := premises ++ collectConsts proof
  | none => pure ()
  -- Eliminar duplicados y filtrar el propio nombre
  let filtered := premises.eraseDups.filter (· != constName)
  return filtered

/--
Punto de entrada: recibe un nombre de teorema, imprime sus premisas en JSON.
Uso: lake env lean --run GetPremises.lean irrational_sqrt_two
-/
unsafe def main (args : List String) : IO Unit := do
  match args with
  | [nameStr] =>
    let constName := nameStr.toName
    -- Inicializar el entorno cargando Mathlib
    let env ← importModules [{module := `Mathlib}] {}
    -- Ejecutar en MetaM
    match getPremises constName |>.run' {} { env := env } with
    | .ok premises =>
      let jsonStrs := premises.map fun n => s!"\"{n}\""
      IO.println s!"[{", ".join jsonStrs}]"
    | .error e =>
      IO.eprintln s!"Error: {e}"
  | _ =>
    IO.eprintln "Uso: lake env lean --run GetPremises.lean <nombre>"
