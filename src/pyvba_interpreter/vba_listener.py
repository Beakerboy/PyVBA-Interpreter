from typing import TypeVar
from antlr4_vba.vbaParser import vbaParser as Parser
from antlr4_vba.vbaParserListener import vbaParserListener as Listener
from vba_stdlib.literal_factory import literal_from_string
from .symbol_table import FunctionType, ParamDefinition, SymbolTable
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
                "type": FunctionType.PROJECT,
                "modules": {}
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
            "type": FunctionType.MODULE,
            "functions": {}
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
            "type": FunctionType.FUNCTION,
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
        modules = self.table.definitions[self.project_name.lower()]["modules"]
        funcs = modules[self.module_name.lower()]["functions"]
        if name.lower() in funcs:
            raise VbaCompileException(f"Ambiguous name detected: {name}")
        # Save the context (subtree) so the Visitor can find it later
        params = self._get_params(ctx.procedureParameters())
        funcs[name.lower()] = {
            "name": name.lower(),
            "type": FunctionType.SUB,
            "project": self.project_name,
            "module": self.module_name.lower(),
            "handle": ctx,
            "params": params,
            "extra": {}
        }

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
                    name = pos_params.positionalParam(i).getText().lower()
                    param: ParamDefinition = {
                        "name": name,
                        "optional": False,
                        "default": None
                    }
                    params.append(param)
                    i += 1
            i = 0
            if parameter_list.optionalParameters() is not None:
                opt_params = parameter_list.optionalParameters()
                while opt_params.optionalParam(i) is not None:
                    opt_param = opt_params.optionalParam(i)
                    name = opt_param.paramDcl().getText().lower()
                    # ToDo, evaluate that the ConstantExpression meets the
                    # static semantics outlined in 5.6.16.1
                    default = None
                    if opt_param.defaultValue() is not None:
                        def_val = opt_param.defaultValue()
                        default = literal_from_string(
                            def_val.constantExpression().getText()
                        )
                    param = {
                        "name": name,
                        "optional": True,
                        "default": default
                    }
                    params.append(param)
                    i += 1
        return params
