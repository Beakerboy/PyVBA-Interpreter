from typing import Any, TypeVar
from antlr4_vba.vbaParser import vbaParser as Parser
from antlr4_vba.vbaParserListener import vbaParserListener as Listener
from vba_types import literal_from_string, VBAVariable
from .symbol_table import ParamDefinition, SymbolTable
from .Exceptions.vba_compile_exception import VbaCompileException
from .Exceptions.vba_exception import VbaException


T = TypeVar('T', bound='VbaListener')


class VbaListener(Listener):
    def __init__(self: T, project: str, table: SymbolTable) -> None:
        self.table = table
        self.module_name = ""
        self.project_name = project.lower()
        self._in_procedure = False
        self._local_vars: dict[str, dict[str, Any]] = {}
        if self.project_name not in self.table.definitions:
            self.table.definitions[self.project_name] = {
                "name": self.project_name,
                "type": "project",
                "modules": {},
                "extra": {}
            }

    def enterProceduralModuleHeader(                               # noqa: N802
            self: T,
            ctx: Parser.ProceduralModuleHeaderContext) -> None:
        self.module_name = ctx.STRINGLITERAL().getText()[1:-1]
        if self.module_name.lower() == "vba":
            raise VbaException(
                "Name conflicts with existing module, project, or object "
                "library")
        project = self.table.definitions[self.project_name]
        project["modules"][self.module_name.lower()] = {
            "name": self.module_name.lower(),
            "type": "module",
            "functions": {},
            "extra": {}
        }

    def enterFunctionDeclaration(                                  # noqa: N802
            self: T,
            ctx: Parser.FunctionDeclarationContext) -> None:
        name = ctx.functionName().getText()
        mod_name = self.module_name.lower()
        modules = self.table.definitions[self.project_name.lower()]["modules"]
        funcs = modules[mod_name]["functions"]
        if name.lower() in funcs:
            raise VbaCompileException(f"Ambiguous name detected: {name}")
        # Save the context (subtree) so the Visitor can find it later
        params = self._get_params(ctx.procedureParameters())
        self._start_procedure_scope(params)
        funcs[name.lower()] = {
            "name": name.lower(),
            "type": "function",
            "module": self.module_name.lower(),
            "project": self.project_name,
            "handle": ctx,
            "params": params,
            "extra": {}
        }

    def enterSubroutineDeclaration(                                # noqa: N802
            self: T,
            ctx: Parser.SubroutineDeclarationContext) -> None:
        name = ctx.subroutineName().getText()
        mod_name = self.module_name.lower()
        modules = self.table.definitions[self.project_name.lower()]["modules"]
        funcs = modules[mod_name]["functions"]
        if name.lower() in funcs:
            raise VbaCompileException(f"Ambiguous name detected: {name}")
        # Save the context (subtree) so the Visitor can find it later
        params = self._get_params(ctx.procedureParameters())
        self._start_procedure_scope(params)
        funcs[name.lower()] = {
            "name": name.lower(),
            "type": "sub",
            "project": self.project_name,
            "module": self.module_name.lower(),
            "handle": ctx,
            "params": params,
            "extra": {}
        }

    def exitFunctionDeclaration(                                   # noqa: N802
            self: T,
            ctx: Parser.FunctionDeclarationContext) -> None:
        self._end_procedure_scope()

    def exitSubroutineDeclaration(                                 # noqa: N802
            self: T,
            ctx: Parser.SubroutineDeclarationContext) -> None:
        self._end_procedure_scope()

    def _start_procedure_scope(
            self: T, params: list[ParamDefinition]) -> None:
        self._in_procedure = True
        self._local_vars = {}
        for param in params:
            self._local_vars[param["name"].lower()] = {
                "fixed_array": False,
                "type_name": None,
            }

    def _end_procedure_scope(self: T) -> None:
        self._in_procedure = False
        self._local_vars = {}

    @staticmethod
    def _extract_as_clause_type(
            as_clause: Parser.AsClauseContext | None) -> str | None:
        if as_clause is None:
            return None
        text = as_clause.getText().lower()
        if text.startswith("as"):
            return text[2:].strip()
        return text

    def enterLocalVariableDeclaration(                             # noqa: N802
            self: T,
            ctx: Parser.LocalVariableDeclarationContext) -> None:
        if not self._in_procedure or ctx.variableDeclarationList() is None:
            return
        dcl_list = ctx.variableDeclarationList()
        i = 0
        while dcl_list.variableDcl(i) is not None:
            untyped = dcl_list.variableDcl(i).untypedVariableDcl()
            if untyped is not None:
                name = untyped.ambiguousIdentifier().getText().lower()
                if name in self._local_vars:
                    raise VbaCompileException(
                        "Duplicate declaration in current scope"
                    )
                type_name = self._extract_as_clause_type(untyped.asClause())
                array_clause = untyped.arrayClause()
                fixed_array = (
                    array_clause is not None
                    and array_clause.arrayDim() is not None
                    and array_clause.arrayDim().boundsList() is not None
                )
                self._local_vars[name] = {
                    "fixed_array": fixed_array,
                    "type_name": type_name,
                }
            i += 1

    def enterRedimStatement(                                       # noqa: N802
            self: T,
            ctx: Parser.RedimStatementContext) -> None:
        if not self._in_procedure or ctx.redimDeclarationList() is None:
            return
        dcl_list = ctx.redimDeclarationList()
        i = 0
        while dcl_list.redimVariableDcl(i) is not None:
            dcl = dcl_list.redimVariableDcl(i)
            untyped = dcl.redimUntypedDcl()
            typed = dcl.redimTypedVariableDcl()
            as_clause = None
            if untyped is not None:
                name = untyped.untypedName().getText().lower()
                dyn_clause = untyped.dynamicArrayClause()
                if dyn_clause is not None:
                    as_clause = dyn_clause.asClause()
            elif typed is not None:
                ident = typed.typedName().ambiguousIdentifier()
                name = ident.getText().lower()
            else:
                i += 1
                continue

            new_type = self._extract_as_clause_type(as_clause)
            if name in self._local_vars:
                info = self._local_vars[name]
                if info["fixed_array"]:
                    raise VbaCompileException("Array already dimensioned")
                if as_clause is not None and new_type != info["type_name"]:
                    raise VbaCompileException(
                        "Can't change data types of array elements"
                    )
            else:
                self._local_vars[name] = {
                    "fixed_array": False,
                    "type_name": new_type,
                }
            i += 1

    def _get_params(
            self: T,
            ctx: Parser.ProcedureParametersContext) -> list[ParamDefinition]:
        params = []
        parameter_list = ctx.parameterList()
        i = 0
        if parameter_list is not None:
            if parameter_list.positionalParameters() is not None:
                pos_params = parameter_list.positionalParameters()
                while pos_params.positionalParam(i) is not None:
                    pos_param = pos_params.positionalParam(i)
                    untyped_name = pos_param.paramDcl().untypedNameParamDcl()
                    name = untyped_name.ambiguousIdentifier().getText().lower()
                    mech = "byref"
                    if pos_param.parameterMechanism() is not None:
                        mech = pos_param.parameterMechanism().getText().lower()
                    if untyped_name.parameterType() is None:
                        var = VBAVariable()
                    else:
                        type_expres = untyped_name.parameterType()
                        type = type_expres.typeExpression().getText().lower()
                        var = VBAVariable(type)
                    param: ParamDefinition = {
                        "name": name,
                        "var": var,
                        "optional": False,
                        "default": None,
                        "mech": mech
                    }
                    params.append(param)
                    i += 1
            i = 0
            if parameter_list.optionalParameters() is not None:
                opt_params = parameter_list.optionalParameters()
                while opt_params.optionalParam(i) is not None:
                    opt_param = opt_params.optionalParam(i)
                    name = opt_param.paramDcl().getText().lower()
                    mech = "byref"
                    prefix = opt_param.optionalPrefix()
                    if prefix.parameterMechanism() is not None:
                        mech = prefix.parameterMechanism().getText().lower()
                    # ToDo, evaluate that the ConstantExpression meets the
                    # static semantics outlined in 5.6.16.1
                    default = None
                    if opt_param.defaultValue() is not None:
                        def_val = opt_param.defaultValue()
                        default = literal_from_string(
                            def_val.constantExpression().getText()
                        )
                    var = VBAVariable(value=default)
                    param = {
                        "name": name,
                        "optional": True,
                        "default": default,
                        "var": var,
                        "mech": mech
                    }
                    params.append(param)
                    i += 1
        return params
