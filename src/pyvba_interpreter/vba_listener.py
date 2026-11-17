from typing import TypeVar
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
        funcs[name.lower()] = {
            "name": name.lower(),
            "type": "sub",
            "project": self.project_name,
            "module": self.module_name.lower(),
            "handle": ctx,
            "params": params,
            "extra": {}
        }

    _TYPE_SUFFIXES = {
        "%": "integer",
        "&": "long",
        "!": "single",
        "#": "double",
        "@": "currency",
        "$": "string",
        "^": "longlong",
    }

    def _parse_param_dcl(
            self: T,
            param_dcl: Parser.ParamDclContext) -> tuple[str, str]:
        if param_dcl.typedNameParamDcl() is not None:
            typed_name = param_dcl.typedNameParamDcl().typedName()
            name = typed_name.ambiguousIdentifier().getText().lower()
            suffix = typed_name.typeSuffix().getText()
            declared_type = self._TYPE_SUFFIXES.get(suffix, "variant")
            return (name, declared_type)
        untyped_name = param_dcl.untypedNameParamDcl()
        name = untyped_name.ambiguousIdentifier().getText().lower()
        if untyped_name.parameterType() is None:
            return (name, "variant")
        type_expres = untyped_name.parameterType()
        declared_type = type_expres.typeExpression().getText().lower()
        return (name, declared_type)

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
                    name, declared_type = self._parse_param_dcl(
                        pos_param.paramDcl()
                    )
                    mech = "byref"
                    if pos_param.parameterMechanism() is not None:
                        mech = pos_param.parameterMechanism().getText().lower()
                    var = VBAVariable(declared_type)
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
                    name, declared_type = self._parse_param_dcl(
                        opt_param.paramDcl()
                    )
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
                    var = VBAVariable(declared_type, value=default)
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
