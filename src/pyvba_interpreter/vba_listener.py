from typing import TypeVar
from antlr4_vba.vbaParser import vbaParser as Parser
from antlr4_vba.vbaParserListener import vbaParserListener as Listener
from vba_stdlib.literal_factory import literal_from_string
from .symbol_table import ParamDefinition, SymbolTable
from .Exceptions.vba_compile_exception import VbaCompileException


T = TypeVar('T', bound='VbaListener')


class VbaListener(Listener):
    def __init__(self: T, table: SymbolTable) -> None:
        self.table = table

    def enterFunctionDeclaration(                                  # noqa: N802
            self: T,
            ctx: Parser.FunctionDeclarationContext) -> None:
        name = ctx.functionName().getText().lower()
        if name in self.table.definitions:
            raise VbaCompileException(f"Ambiguous name detected: {name}")
        # Save the context (subtree) so the Visitor can find it later
        params = self._get_params(ctx.procedureParameters())
        self.table.definitions[name] = {
            "type": "function",
            "handle": ctx.procedureBody(),
            "params": params
        }

    def enterSubroutineDeclaration(                                # noqa: N802
            self: T,
            ctx: Parser.SubroutineDeclarationContext) -> None:
        name = ctx.subroutineName().getText().lower()
        if name in self.table.definitions:
            raise VbaCompileException(f"Ambiguous name detected: {name}")
        # Save the context (subtree) so the Visitor can find it later
        params = self._get_params(ctx.procedureParameters())
        self.table.definitions[name] = {
            "type": "sub",
            "handle": ctx.procedureBody(),
            "params": params
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
