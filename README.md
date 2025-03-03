# tools-shared
The shared tools for Lynx repositories

## [Usage]
### Install Habitat
We use [Habitat](https://github.com/lynx-family/habitat) to manage dependencies. Please install it first.

### Pull the source code
You can download the code of tools-shared repository to your local machine via git clone or any other method.

### Synchronize dependencies.
```bash
cd tools-shared
./hab sync -f .
```
### Initialize the environment.
After this step, a sub-command "git lynx check" will be added to the git tool.
```bash
source envsetup.sh
```

### Run check
```bash
git lynx check --help
git lynx check --list
git lynx check
```

### Custom configuration
tools-shared has built-in default configurations. To meet your needs, you can manually provide a configuration file named tools-shared.yml in the root directory of the repository to override the default ones.

You can continue to check the detailed configuration information [here](./docs/README_CONFIGURATION.md).


### Contributing Guide
We welcome you to join and become a member of Lynx Authors. It's people like you that make this project great.

Please refer to our [contributing guide](CONTRIBUTING.md) for details.


## [License]
tools-shared is Apache licensed, as found in the [LICENSE](LICENSE) file.
