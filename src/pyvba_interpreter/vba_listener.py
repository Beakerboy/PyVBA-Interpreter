"""
VBA declaration listener.

This ANTLR listener performs the initial symbol discovery pass over a VBA
module. Its primary responsibility is to populate the global SymbolTable
with projects, modules, procedures, and parameter metadata before any
execution or interpretation occurs.

The listener does not execute VBA code. Instead, it traverses the parse
tree and records information needed by later compilation, semantic
analysis, and execution phases.

Responsibilities:
    - Register VBA projects.
    - Register modules within projects.
    - Register functions and subroutines.
    - Extract procedure parameter definitions.
    - Detect naming conflicts within a module.
    - Store ANTLR parse contexts for later execution by visitors.

The resulting symbol table provides a searchable catalog of all discovered
procedures and their signatures.
"""

from typing import TypeVar
from antlr4_vba.vbaParser import vbaParser as Parser
from antlr4_vba.vbaParserListener import vbaParserListener as Listener
from vba_types import literal_from_string, VBAVariable
from .symbol_table import ParamDefinition, SymbolTable
from .Exceptions.vba_compile_exception import VbaCompileException
from .Exceptions.vba_exception import VbaException


T = TypeVar('T', bound='VbaListener')


class VbaListener(Listener):
    """
    ANTLR listener used to build VBA symbol definitions.

    During parse tree traversal, this listener discovers and registers
    modules, functions, subroutines, and parameters into the global
    SymbolTable.

    The listener stores procedure parse-tree contexts directly in the
    symbol table so that later execution phases can locate and execute
    procedure bodies without rebuilding the parse tree.

    Attributes:
        table:
            Global symbol table being populated.

        module_name:
            Name of the module currently being processed.

        project_name:
            Name of the current VBA project in normalized lowercase form.
    """
    
    def __init__(self: T, project: str, table: SymbolTable) -> None:
        """
        Initialize a listener for a VBA project.

        Creates a project definition in the symbol table if one does not
        already exist.

        Args:
            project:
                Name of the VBA project being parsed.

            table:
                Symbol table that will receive discovered definitions.

        Returns:
            None
        """
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
        """
        Process a module declaration.

        Triggered when the parser enters a procedural module header.
        Creates a module definition under the current project and stores
        it in the symbol table.

        VBA reserves the name "VBA" for the intrinsic object library.
        Attempting to create a module with this name results in a compile
        error.

        Args:
            ctx:
                Parse tree context representing the module header.

        Raises:
            VbaException:
                If the module name conflicts with the built-in VBA library.

        Returns:
            None
        """
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
        """
        Register a VBA Function procedure.

        Triggered when a Function declaration is encountered. Extracts
        the procedure signature and stores metadata in the current
        module definition.

        The ANTLR context is preserved so later execution phases can
        locate the function body directly from the symbol table.

        Args:
            ctx:
                Parse tree context representing a Function declaration.

        Raises:
            VbaCompileException:
                If another procedure with the same name already exists
                in the module.

        Returns:
            None
        """
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
        """
        Register a VBA Sub procedure.

        Triggered when a Sub declaration is encountered. Extracts
        parameter information and stores the procedure definition
        within the current module.

        The ANTLR parse context is retained so that a later visitor
        can execute or analyze the procedure body.

        Args:
            ctx:
                Parse tree context representing a Sub declaration.

        Raises:
            VbaCompileException:
                If another procedure with the same name already exists
                in the module.

        Returns:
            None
        """
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

    def _get_params(
            self: T,
            ctx: Parser.ProcedureParametersContext) -> list[ParamDefinition]:
        """
        Extract procedure parameter definitions.

        Converts ANTLR parameter declarations into ParamDefinition
        structures that can be stored in the symbol table and later
        used during procedure invocation.

        Supported parameter metadata includes:
            - Name
            - Data type
            - ByRef/ByVal passing mechanism
            - Optional status
            - Default value
            - Backing VBAVariable instance

        Both positional and optional parameter lists are processed
        and returned in declaration order.

        For typed parameters, a VBAVariable is initialized using the
        declared VBA type. Untyped parameters default to Variant-like
        behavior determined by VBAVariable.

        Optional parameter default values are converted from VBA
        literal syntax into runtime values using literal_from_string().

        Args:
            ctx:
                Parse tree context containing procedure parameter
                declarations.

        Returns:
            A list of ParamDefinition objects describing the
            procedure's parameters.

        Notes:
            Validation of VBA constant-expression semantics for
            optional parameter defaults is not yet implemented.
            See VBA specification section 5.6.16.1.
        """
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
