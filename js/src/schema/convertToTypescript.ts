import { compileFromFile } from 'json-schema-to-typescript'
import * as path from 'path'
import * as fs from "fs";
import  commandLineArgs = require('command-line-args')

const optionalDefinitions = [
    { name: 'out', alias: 'o', type: String },
    { name: 'dry_run', alias: 'd', type: Boolean, defaultOption: false},
]
const options = commandLineArgs(optionalDefinitions);

const READ_ROOT_DIR = "../schema"

function convertObject(fileName: string, relativeOutputPath: string) {
    console.log(`Converting file ${fileName} and writing to dir ${relativeOutputPath}`);
    const dirname = path.dirname(relativeOutputPath)
    if (options.dry_run === true) {
        console.log('...but this is a dry run...')
        return
    }
    if (!fs.existsSync(dirname)) {
        fs.mkdirSync(dirname, {recursive: true, mode: '0777'});
    }
    compileFromFile(fileName).then(ts => fs.writeFileSync(relativeOutputPath, ts));
}

function convertDirectory(dir_path: string, relative_output_path: string) {
    fs.readdir(dir_path, function(ex, items) {
        if (ex !== null) {
            throw ex;
        }
        for (let item of items) {
            const resolvedLocalPath: string = path.join(dir_path, item);
            const resolvedRelativeOutputPath: string = path.join(relative_output_path, item).replace(/\.json$/, '.ts');
            if (fs.lstatSync(resolvedLocalPath).isDirectory()) {
                convertDirectory(resolvedLocalPath, resolvedRelativeOutputPath);
            }
            if (path.extname(item) !== ".json") {
                console.log(`skipping ${item}`);
                continue;
            }
            convertObject(resolvedLocalPath, resolvedRelativeOutputPath);
        }
    })
}

function main() {
    const absoluteOutput: string = path.resolve(options.out);
    const absoluteInput: string = path.resolve(READ_ROOT_DIR);
    console.log(`Writing files to ${options.out}`);
    convertDirectory(absoluteInput, absoluteOutput);
}

if (require.main === module) {
    main();
}
