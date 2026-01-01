import junitbuild.extensions.markerCoordinates

plugins {
	`kotlin-dsl`
}

dependencies {
	implementation("junitbuild.base:dsl-extensions")
	implementation(libs.plugins.jreleaser.markerCoordinates)
	constraints {
		implementation("org.eclipse.jgit:org.eclipse.jgit") {
			version {
				require("6.10.1.202505221210-r")
			}
			because("Workaround for CVE-2025-4949")
		}
		implementation("org.apache.tika:tika-core") {
			version {
				require("3.2.2")
			}
			because("Workaround for CVE-2025-66516")
		}
		implementation("com.fasterxml.jackson.core:jackson-core") {
			version {
				require("2.21.1")
			}
			because("Workaround for GHSA-72hv-8253-57qq")
		}
		implementation("org.codehaus.plexus:plexus-utils") {
			version {
				require("3.6.1")
			}
			because("Workaround for CVE-2025-67030")
		}
	}
}
