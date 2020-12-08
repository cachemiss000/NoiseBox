"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const json_schema_to_typescript_1 = require("json-schema-to-typescript");
const path = require("path");
const fs = require("fs");
const commandLineArgs = require("command-line-args");
const optionalDefinitions = [
    { name: 'out', alias: 'o', type: String },
    { name: 'dry_run', alias: 'd', type: Boolean, defaultOption: false },
];
const options = commandLineArgs(optionalDefinitions);
const READ_ROOT_DIR = "../schema";
function convertObject(fileName, relativeOutputPath) {
    console.log(`Converting file ${fileName} and writing to dir ${relativeOutputPath}`);
    const dirname = path.dirname(relativeOutputPath);
    if (options.dry_run === true) {
        console.log('...but this is a dry run...');
        return;
    }
    if (!fs.existsSync(dirname)) {
        fs.mkdirSync(dirname, { recursive: true, mode: '0777' });
    }
    json_schema_to_typescript_1.compileFromFile(fileName).then(ts => fs.writeFileSync(relativeOutputPath, ts));
}
function convertDirectory(dir_path, relative_output_path) {
    fs.readdir(dir_path, function (ex, items) {
        if (ex !== null) {
            throw ex;
        }
        for (let item of items) {
            const resolvedLocalPath = path.join(dir_path, item);
            const resolvedRelativeOutputPath = path.join(relative_output_path, item).replace(/\.json$/, '.ts');
            if (fs.lstatSync(resolvedLocalPath).isDirectory()) {
                convertDirectory(resolvedLocalPath, resolvedRelativeOutputPath);
            }
            if (path.extname(item) !== ".json") {
                console.log(`skipping ${item}`);
                continue;
            }
            convertObject(resolvedLocalPath, resolvedRelativeOutputPath);
        }
    });
}
function main() {
    const absoluteOutput = path.resolve(options.out);
    const absoluteInput = path.resolve(READ_ROOT_DIR);
    console.log(`Writing files to ${options.out}`);
    convertDirectory(absoluteInput, absoluteOutput);
}
if (require.main === module) {
    main();
}
//# sourceMappingURL=convertToTypescript.js.map