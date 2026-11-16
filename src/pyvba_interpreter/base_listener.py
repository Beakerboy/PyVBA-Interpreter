"""
Base listener implementation used by all declaration listeners.

This class provides shared functionality for parse-tree listeners that
populate the symbol table. It contains project initialization logic and
helper methods for extracting procedure metadata.

Concrete listeners such as ModuleListener and ClassListener should inherit
from this class and implement grammar-specific event handlers.
"""

from typing import TypeVar

from antlr4_vba.vbaParser import vbaParser as Parser
from antlr4_vba.vbaParserListener import vbaParserListener as Listener

from vba_types import literal_from_string, VBAVariable

from .symbol_table import ParamDefinition, SymbolTable

T = TypeVar("T", bound="BaseListener")


class BaseListener(Listener):
    """
    Base class for listeners that populate VBA symbol definitions.

    Attributes:
        table:
            Global symbol table being populated.

        project_name:
            Name of the current VBA project in normalized lowercase form.
    """

    def __init__(self: T, project: str, table: SymbolTable) -> None:
        """
        Initialize the listener and ensure the project exists within the
        symbol table.

        Args:
            project:
                VBA project name.

            table:
                Symbol table receiving discovered declarations.
        """
        self.table = table
        self.project_name = project.lower()

        if self.project_name not in self.table.definitions:
            self.table.definitions[self.project_name] = {
                "name": self.project_name,
                "type": "project",
                "modules": {},
                "classes": {},
                "extra": {}
            }

    def _get_params(
            self: T,
            ctx: Parser.ProcedureParametersContext
    ) -> list[ParamDefinition]:
        """
        Extract parameter definitions from a procedure declaration.

        Converts ANTLR parameter declarations into ParamDefinition
        dictionaries suitable for storage in the symbol table.

        Args:
            ctx:
                ProcedureParameters parse context.

        Returns:
            List of parameter definitions.
        """
        params: list[ParamDefinition] = []

        parameter_list = ctx.parameterList()

        if parameter_list is None:
            return params

        i = 0

        if parameter_list.positionalParameters() is not None:
            pos_params = parameter_list.positionalParameters()

            while pos_params.positionalParam(i) is not None:
                pos_param = pos_params.positionalParam(i)

                param_dcl = pos_param.paramDcl()

                if param_dcl.untypedNameParamDcl() is not None:
                    param_decl = param_dcl.untypedNameParamDcl()

                    name = (
                        param_decl
                        .ambiguousIdentifier()
                        .getText()
                        .lower()
                    )

                    if param_decl.parameterType() is None:
                        var = VBAVariable()
                    else:
                        type_name = (
                            param_decl
                            .parameterType()
                            .typeExpression()
                            .getText()
                            .lower()
                        )
                        var = VBAVariable(type_name)

                else:
                    param_decl = param_dcl.typedNameParamDcl()

                    name = (
                        param_decl
                        .ambiguousIdentifier()
                        .getText()
                        .lower()
                    )

                    var = VBAVariable()

                mech = "byref"

                if pos_param.parameterMechanism() is not None:
                    mech = (
                        pos_param
                        .parameterMechanism()
                        .getText()
                        .lower()
                    )

                params.append({
                    "name": name,
                    "var": var,
                    "optional": False,
                    "default": None,
                    "mech": mech
                })

                i += 1

        i = 0

        if parameter_list.optionalParameters() is not None:
            opt_params = parameter_list.optionalParameters()

            while opt_params.optionalParam(i) is not None:
                opt_param = opt_params.optionalParam(i)

                param_dcl = opt_param.paramDcl()

                if param_dcl.untypedNameParamDcl() is not None:
                    name = (
                        param_dcl
                        .untypedNameParamDcl()
                        .ambiguousIdentifier()
                        .getText()
                        .lower()
                    )
                else:
                    name = (
                        param_dcl
                        .typedNameParamDcl()
                        .ambiguousIdentifier()
                        .getText()
                        .lower()
                    )

                mech = "byref"

                prefix = opt_param.optionalPrefix()

                if prefix.parameterMechanism() is not None:
                    mech = (
                        prefix
                        .parameterMechanism()
                        .getText()
                        .lower()
                    )

                default = None

                if opt_param.defaultValue() is not None:
                    default = literal_from_string(
                        opt_param.defaultValue()
                        .constantExpression()
                        .getText()
                    )

                var = VBAVariable(value=default)

                params.append({
                    "name": name,
                    "optional": True,
                    "default": default,
                    "var": var,
                    "mech": mech
                })

                i += 1

        return params
