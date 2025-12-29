import {
    DataExtractionResult,
    DataExtractorId,
} from "@hediet/debug-visualizer-data-extraction";
import { hotClass, registerUpdateReconciler } from "@hediet/node-reload";
import * as vscode from "vscode";
import * as path from "path";
import { Config } from "../Config";
import { DebugSessionProxy } from "../proxies/DebugSessionProxy";
import { DebuggerViewProxy } from "../proxies/DebuggerViewProxy";
import { FormattedMessage } from "../webviewContract";
import {
    DebugSessionVisualizationSupport,
    GetVisualizationDataArgs,
    VisualizationBackend,
    VisualizationBackendBase,
} from "./VisualizationBackend";
import { parseEvaluationResultFromGenericDebugAdapter } from "./parseEvaluationResultFromGenericDebugAdapter";

registerUpdateReconciler(module);

/**
 * C++ Visualization Engine for GDB/LLDB debug adapters.
 * 
 * This engine automatically injects the universal_vis.py script into GDB
 * and wraps expressions with the `vis` command to generate graph visualization data.
 * 
 * Supported debug adapters:
 * - cppdbg: Microsoft C/C++ Extension (GDB/LLDB backend)
 * - cppvsdbg: Microsoft C/C++ Extension (Windows MSVC debugger)
 * - lldb: CodeLLDB extension
 * - gdb: Native GDB debug adapter
 */
@hotClass(module)
export class CppEvaluationEngine implements DebugSessionVisualizationSupport {
    constructor(
        private readonly debuggerView: DebuggerViewProxy,
        private readonly config: Config
    ) { }

    createBackend(
        session: DebugSessionProxy
    ): VisualizationBackend | undefined {
        // Supported C++ debug adapter types
        const supportedDebugAdapters = [
            "cppdbg",      // Microsoft C/C++ Extension (GDB/LLDB)
            "cppvsdbg",    // Microsoft C/C++ Extension (Windows MSVC)
            "lldb",        // CodeLLDB extension
            "gdb",         // Native GDB adapter
        ];

        if (supportedDebugAdapters.includes(session.session.type)) {
            return new CppVisualizationBackend(
                session,
                this.debuggerView,
                this.config
            );
        }
        return undefined;
    }
}

/**
 * Backend that handles C++ visualization via GDB Python script injection.
 * 
 * Workflow:
 * 1. On first evaluation, inject universal_vis.py into GDB via "source" command
 * 2. For each expression, wrap it with "vis <expr>" command
 * 3. Parse the JSON output and return visualization data
 */
export class CppVisualizationBackend extends VisualizationBackendBase {
    public readonly expressionLanguageId = "cpp";

    // Track script injection state per session
    private scriptInjected: boolean = false;
    private injectionAttempted: boolean = false;
    private injectionError: string | null = null;

    constructor(
        debugSession: DebugSessionProxy,
        debuggerView: DebuggerViewProxy,
        private readonly config: Config
    ) {
        super(debugSession, debuggerView);
    }

    protected getContext(): "watch" | "repl" {
        // Use "repl" context so results are not truncated by the debugger
        return "repl";
    }

    /**
     * Get the absolute path to the universal_vis.py script.
     * Uses vscode.extensions API for cross-platform compatibility.
     */
    private getVisualizationScriptPath(): string {
        // Get the extension by its ID (publisher.name from package.json)
        // For development, we fall back to __dirname-based resolution
        const extension = vscode.extensions.getExtension("antigravity-iti.antigravity-debug-visualizer");

        if (extension) {
            // Production: use extension path
            return path.join(extension.extensionPath, "dist", "resources", "universal_vis.py");
        } else {
            // Development fallback: resolve relative to compiled JS location
            // __dirname will be extension/dist when compiled
            return path.join(__dirname, "resources", "universal_vis.py");
        }
    }

    /**
     * Build the GDB command to source the Python script.
     * Handles different debug adapter command formats.
     */
    private buildSourceCommand(scriptPath: string): string {
        const debugAdapterType = this.debugSession.session.configuration.type;

        // Escape backslashes for Windows paths
        const escapedPath = scriptPath.replace(/\\/g, "\\\\");

        switch (debugAdapterType) {
            case "cppdbg":
                // Microsoft C/C++ uses -exec prefix for GDB/MI commands
                return `-exec source "${escapedPath}"`;

            case "cppvsdbg":
                // Windows MSVC debugger - Python scripts not supported
                // Fall back to raw JSON evaluation
                return "";

            case "lldb":
                // LLDB uses "command script import" for Python
                return `command script import "${escapedPath}"`;

            case "gdb":
                // Native GDB - direct source command
                return `source "${escapedPath}"`;

            default:
                // Default: try GDB-style with -exec prefix
                return `-exec source "${escapedPath}"`;
        }
    }

    /**
     * Build the visualization command for an expression.
     */
    private buildVisCommand(expression: string): string {
        const debugAdapterType = this.debugSession.session.configuration.type;
        const expr = expression.trim();

        switch (debugAdapterType) {
            case "cppdbg":
                // Microsoft C/C++ uses -exec prefix
                return `-exec vis ${expr}`;

            case "cppvsdbg":
                // Windows MSVC - fall back to raw expression
                return expr;

            case "lldb":
                // LLDB - direct command
                return `vis ${expr}`;

            case "gdb":
                // Native GDB
                return `vis ${expr}`;

            default:
                return `-exec vis ${expr}`;
        }
    }

    /**
     * Inject the visualization Python script into the debugger.
     * This only needs to be done once per debug session.
     * 
     * @returns true if injection succeeded or was already done
     */
    private async injectVisualizationScript(): Promise<boolean> {
        // Already injected successfully
        if (this.scriptInjected) {
            return true;
        }

        // Already tried and failed - don't retry
        if (this.injectionAttempted && this.injectionError) {
            return false;
        }

        this.injectionAttempted = true;

        const scriptPath = this.getVisualizationScriptPath();
        const sourceCommand = this.buildSourceCommand(scriptPath);

        // MSVC debugger doesn't support Python scripts
        if (!sourceCommand) {
            this.injectionError = "Python scripts not supported for this debugger type";
            return false;
        }

        const frameId = this.debuggerView.getActiveStackFrameId(this.debugSession);

        try {
            await this.debugSession.evaluate({
                expression: sourceCommand,
                frameId,
                context: this.getContext(),
            });

            this.scriptInjected = true;
            console.log(`[Antigravity] Successfully injected visualization script: ${scriptPath}`);
            return true;

        } catch (error: any) {
            this.injectionError = error.message;
            console.warn(`[Antigravity] Failed to inject visualization script: ${error.message}`);
            console.warn(`[Antigravity] Script path was: ${scriptPath}`);
            console.warn(`[Antigravity] Command was: ${sourceCommand}`);
            return false;
        }
    }

    /**
     * Main entry point: get visualization data for an expression.
     */
    public async getVisualizationData({
        expression,
        preferredExtractorId,
    }: GetVisualizationDataArgs): Promise<
        | { kind: "data"; result: DataExtractionResult }
        | { kind: "error"; message: FormattedMessage }
    > {
        const frameId = this.debuggerView.getActiveStackFrameId(this.debugSession);

        // Step 1: Try to inject the visualization script
        const injectionSuccess = await this.injectVisualizationScript();

        if (!injectionSuccess) {
            // Fallback: try to evaluate expression as raw JSON
            return this.fallbackToGenericVisualization(expression, frameId);
        }

        // Step 2: Build and execute the visualization command
        const visCommand = this.buildVisCommand(expression);

        try {
            const reply = await this.debugSession.evaluate({
                expression: visCommand,
                frameId,
                context: this.getContext(),
            });

            // Step 3: Clean up and parse the result
            let result = this.cleanDebuggerOutput(reply.result);

            return parseEvaluationResultFromGenericDebugAdapter(result, {
                debugAdapterType: this.debugSession.session.configuration.type,
            });

        } catch (error: any) {
            return this.handleEvaluationError(error, expression, visCommand);
        }
    }

    /**
     * Clean up debugger output to extract pure JSON.
     */
    private cleanDebuggerOutput(result: string): string {
        // Remove leading/trailing whitespace
        result = result.trim();

        // GDB might prefix with "$N = " (e.g., "$1 = {...}")
        const gdbPrefixMatch = result.match(/^\$\d+\s*=\s*/);
        if (gdbPrefixMatch) {
            result = result.slice(gdbPrefixMatch[0].length);
        }

        // Extract JSON object if wrapped in other content
        const jsonMatch = result.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
            result = jsonMatch[0];
        }

        // Handle escaped quotes from debugger output
        result = result.replace(/\\"/g, '"');
        result = result.replace(/\\'/g, "'");
        result = result.replace(/\\\\/g, "\\");

        return result;
    }

    /**
     * Handle evaluation errors with helpful messages.
     */
    private handleEvaluationError(
        error: any,
        expression: string,
        visCommand: string
    ): { kind: "error"; message: FormattedMessage } {
        const errorMessage = error.message || String(error);

        // Variable not found
        if (errorMessage.includes("No symbol") || errorMessage.includes("not found")) {
            return {
                kind: "error",
                message: {
                    kind: "list",
                    items: [
                        "Variable not found in current scope:",
                        { kind: "code", content: expression },
                        "Make sure you're stopped at a breakpoint where this variable is visible.",
                    ],
                },
            };
        }

        // vis command not recognized - script not loaded
        if (errorMessage.includes("vis") && errorMessage.includes("Undefined command")) {
            return {
                kind: "error",
                message: {
                    kind: "list",
                    items: [
                        "The visualization script is not loaded.",
                        "The 'vis' command was not recognized by GDB.",
                        {
                            kind: "inlineList",
                            items: [
                                "Try manually loading the script:",
                                { kind: "code", content: `source "${this.getVisualizationScriptPath()}"` },
                            ],
                        },
                    ],
                },
            };
        }

        // Python not available in GDB
        if (errorMessage.includes("Python") || errorMessage.includes("python")) {
            return {
                kind: "error",
                message: {
                    kind: "list",
                    items: [
                        "GDB Python support is required but may not be available.",
                        "Make sure your GDB was compiled with Python support.",
                        "On Ubuntu/Debian: sudo apt install gdb python3",
                    ],
                },
            };
        }

        // Generic error
        return {
            kind: "error",
            message: {
                kind: "list",
                items: [
                    "An error occurred while evaluating the expression:",
                    errorMessage,
                    `Debug adapter type: ${this.debugSession.session.configuration.type}`,
                    {
                        kind: "inlineList",
                        items: [
                            "Command sent:",
                            { kind: "code", content: visCommand },
                        ],
                    },
                ],
            },
        };
    }

    /**
     * Fallback visualization when script injection fails.
     * Tries to parse the expression result as raw JSON.
     */
    private async fallbackToGenericVisualization(
        expression: string,
        frameId: number | undefined
    ): Promise<
        | { kind: "data"; result: DataExtractionResult }
        | { kind: "error"; message: FormattedMessage }
    > {
        try {
            const reply = await this.debugSession.evaluate({
                expression,
                frameId,
                context: this.getContext(),
            });

            // Try to parse as JSON directly
            return parseEvaluationResultFromGenericDebugAdapter(reply.result, {
                debugAdapterType: this.debugSession.session.configuration.type,
            });

        } catch (error: any) {
            return {
                kind: "error",
                message: {
                    kind: "list",
                    items: [
                        "Could not visualize the expression.",
                        "The Antigravity visualization script could not be loaded:",
                        this.injectionError || "Unknown error during script injection",
                        "",
                        "Possible solutions:",
                        "1. Make sure GDB has Python support enabled",
                        "2. Check that the debug session is stopped at a breakpoint",
                        {
                            kind: "inlineList",
                            items: [
                                "3. Manually load the script in Debug Console:",
                                { kind: "code", content: `-exec source "${this.getVisualizationScriptPath()}"` },
                            ],
                        },
                    ],
                },
            };
        }
    }

    /**
     * Get the final expression - used by base class.
     * For C++, we handle command building in getVisualizationData directly.
     */
    protected getFinalExpression(args: {
        expression: string;
        preferredExtractorId: DataExtractorId | undefined;
    }): string {
        return this.buildVisCommand(args.expression);
    }
}
