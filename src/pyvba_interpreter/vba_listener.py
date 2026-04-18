class VBADefinitionListener(VBAListener):
    def __init__(self, table):
        self.table = table

    def enterSubStmt(self, ctx):
        name = ctx.IDENTIFIER().getText()
        # Save the context (subtree) so the Visitor can find it later
        self.table.definitions[name] = ctx
